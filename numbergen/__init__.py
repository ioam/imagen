"""
Callable objects that generate numbers according to different distributions.
"""
__version__='$Revision: 8943 $'

import random
import operator

from math import e,pi

import param


class NumberGenerator(param.Parameterized):
    """
    Abstract base class for any object that when called produces a number.

    Primarily provides support for using NumberGenerators in simple
    arithmetic expressions, such as abs((x+y)/z), where x,y,z are
    NumberGenerators or numbers.
    """

    def __call__(self):
        raise NotImplementedError

    # Could define any of Python's operators here, esp. if they have operator or ufunc equivalents
    def __add__      (self,operand): return BinaryOperator(self,operand,operator.add)
    def __sub__      (self,operand): return BinaryOperator(self,operand,operator.sub)
    def __mul__      (self,operand): return BinaryOperator(self,operand,operator.mul)
    def __mod__      (self,operand): return BinaryOperator(self,operand,operator.mod)
    def __pow__      (self,operand): return BinaryOperator(self,operand,operator.pow)
    def __div__      (self,operand): return BinaryOperator(self,operand,operator.div)
    def __truediv__  (self,operand): return BinaryOperator(self,operand,operator.truediv)
    def __floordiv__ (self,operand): return BinaryOperator(self,operand,operator.floordiv)

    def __radd__     (self,operand): return BinaryOperator(self,operand,operator.add,True)
    def __rsub__     (self,operand): return BinaryOperator(self,operand,operator.sub,True)
    def __rmul__     (self,operand): return BinaryOperator(self,operand,operator.mul,True)
    def __rmod__     (self,operand): return BinaryOperator(self,operand,operator.mod,True)
    def __rpow__     (self,operand): return BinaryOperator(self,operand,operator.pow,True)
    def __rdiv__     (self,operand): return BinaryOperator(self,operand,operator.div,True)
    def __rtruediv__ (self,operand): return BinaryOperator(self,operand,operator.truediv,True)
    def __rfloordiv__(self,operand): return BinaryOperator(self,operand,operator.floordiv,True)

    def __neg__ (self): return UnaryOperator(self,operator.neg)
    def __pos__ (self): return UnaryOperator(self,operator.pos)
    def __abs__ (self): return UnaryOperator(self,operator.abs)



class BinaryOperator(NumberGenerator):
    """Applies any binary operator to NumberGenerators or numbers to yield a NumberGenerator."""

    def __init__(self,lhs,rhs,operator,reverse=False,**args):
        """
        Accepts two NumberGenerator operands, an operator, and
        optional arguments to be provided to the operator when calling
        it on the two operands.
        """
        # Note that it's currently not possible to set
        # parameters in the superclass when creating an instance,
        # because **args is used by this class itself.
        super(BinaryOperator,self).__init__()

        if reverse:
            self.lhs=rhs
            self.rhs=lhs
        else:
            self.lhs=lhs
            self.rhs=rhs
        self.operator=operator
        self.args=args

    def __call__(self):
        return self.operator(self.lhs() if callable(self.lhs) else self.lhs,
                             self.rhs() if callable(self.rhs) else self.rhs, **self.args)



class UnaryOperator(NumberGenerator):
    """Applies any unary operator to a NumberGenerator to yield another NumberGenerator."""

    def __init__(self,operand,operator,**args):
        """
        Accepts a NumberGenerator operand, an operator, and
        optional arguments to be provided to the operator when calling
        it on the operand.
        """
        # Note that it's currently not possible to set
        # parameters in the superclass when creating an instance,
        # because **args is used by this class itself.
        super(UnaryOperator,self).__init__()

        self.operand=operand
        self.operator=operator
        self.args=args

    def __call__(self):
        return self.operator(self.operand(),**self.args)



class TimeAwareValue(param.Parameterized):
    """
    Class of objects that have access to a time function and have the
    option using it to generate time dependent values as necessary.

    Some objects may have clear semantics in both time dependent and
    time independent contexts. For instance, objects with random state
    may return a new random value for every call independent of time.
    Alternatively, each value may be held constant as long as a fixed
    time value is returned by time_fn.
    """

    time_dependent = param.Boolean(default=False,  doc="""
       Whether the given time_fn should be used to constrain the
       results generated.""")

    time_fn = param.Callable(default=param.Dynamic.time_fn, doc="""
        Callable used to specify the time that determines the state
        and return value of the object.""")

    def __init__(self, **params):
        super(TimeAwareValue, self).__init__(**params)
        self._check_time_fn()

    def _check_time_fn(self, time_instance=False):
        """
        If time_fn is the global time function supplied by
        param.Dynamic.time_fn, make sure Dynamic parameters are using
        this time function to control their behaviour.

        If time_instance is True, time_fn must be a param.Time instance.
        """
        if time_instance and not isinstance(self.time_fn, param.Time):
            raise AssertionError("%s requires a Time object"
                                 % self.__class__.__name__)

        if self.time_dependent:
            global_timefn = self.time_fn is param.Dynamic.time_fn
            if global_timefn and not param.Dynamic.time_dependent:
                raise AssertionError("Cannot use Dynamic.time_fn as"
                                     " parameters are ignoring time.")



class TimeDependentValue(TimeAwareValue):
    """
    Objects that have access to a time function that determines the
    output value. As a function of time, this type of object should
    allow time values to be randomly jumped forwards or backwards but
    for a given time point, the results should remain constant.

    The time_fn must be an instance of param.Time to ensure all the
    facilities necessary for safely navigating the timeline are
    available.
    """
    time_dependent = param.Boolean(default=True, constant=True,
                                   precedence=-1, doc="""
       TimeDependentValue objects always have time_dependent=True.""")

    def _check_time_fn(self):
        if self.time_dependent is False:
            self.warning("Parameter time_dependent cannot be set to False.")
            p = self.params('time_dependent')
            p.constant = False
            self.time_dependent = True
            p.constant = True
        super(TimeDependentValue,self)._check_time_fn(time_instance=True)



class RandomDistribution(NumberGenerator, TimeAwareValue):
    """
    Python's random module provides the Random class, which can be
    instantiated to give an object that can be asked to generate
    numbers from any of several different random distributions
    (e.g. uniform, Gaussian).

    To make it easier to use these, Numbergen provides here a
    hierarchy of classes, each tied to a particular random
    distribution. This allows setting parameters on creation rather
    than passing them each call, and allows pickling to work properly.

    The underlying random.Random() instance and all its methods can be
    accessed from the 'random_generator' attribute.

    RandomDistributions are TimeAwareValues as they can be set to have
    time dependent or time independent behaviour, toggled by setting
    time_dependent appropriately. By default, the random values
    generated are not coupled to the time returned by the
    time_fn. This can make random values difficult to reproduce as
    returning to a previous time value will not regenerate the
    original value.

    If declared time_dependent, a hash is generated for seeding the
    random state on each call, using a triple consisting of the object
    name, the time returned by time_fn and the value of
    param.random_seed. As a consequence, for a given name and fixed
    value of param.random_seed, the random values generated will be a
    function of time.

    If the object name has not been explicitly set and time_dependent
    is True, a message is generated warning that the default object
    name is dependent on the order of instantiation.
    """
    __abstract = True

    def __init__(self,**params):
        """
        Initialize a new Random() instance and store the supplied
        positional and keyword arguments.

        If seed=X is specified, sets the Random() instance's seed.
        Otherwise, calls the instance's jumpahead() method to get a
        state very likely to be different from any just used.
        """
        self.random_generator = random.Random()

        seed = params.pop('seed', None)
        super(RandomDistribution,self).__init__(**params)

        if seed is not None:
            self.random_generator.seed(seed)
        else:
            self.random_generator.jumpahead(10)

        self._verify_constrained_hash()
        if self.time_dependent:
            self._hash_and_seed()

    def _verify_constrained_hash(self):
        changed_params = dict(self.get_param_values(onlychanged=True))
        if self.time_dependent and ('name' not in changed_params):
            self.warning("Default object name used to set the seed: "
                         "random values conditional on object instantiation order.")

    def _hash_and_seed(self):
        hashval = hash((self.name, self.time_fn(), param.random_seed))
        self.random_generator.seed(hashval)

    def __call__(self):
        if self.time_dependent:
            self._hash_and_seed()


class UniformRandom(RandomDistribution):
    """
    Specified with lbound and ubound; when called, return a random
    number in the range [lbound, ubound).

    See the random module for further details.
    """
    lbound = param.Number(default=0.0,doc="inclusive lower bound")
    ubound = param.Number(default=1.0,doc="exclusive upper bound")

    def __call__(self):
        super(UniformRandom, self).__call__()
        return self.random_generator.uniform(self.lbound,self.ubound)


class UniformRandomOffset(RandomDistribution):
    """
    Identical to UniformRandom, but specified by mean and range.
    When called, return a random number in the range
    [mean - range/2, mean + range/2).

    See the random module for further details.
    """
    mean = param.Number(default=0.0, doc="""
        Mean value""")
    range = param.Number(default=1.0, doc="""
        Difference of maximum and minimum value""")

    def __call__(self):
        super(UniformRandomOffset, self).__call__()
        return self.random_generator.uniform(
                self.mean - self.range / 2.0,
                self.mean + self.range / 2.0)


class UniformRandomInt(RandomDistribution):
    """
    Specified with lbound and ubound; when called, return a random
    number in the inclusive range [lbound, ubound].

    See the randint function in the random module for further details.
    """
    lbound = param.Number(default=0,doc="inclusive lower bound")
    ubound = param.Number(default=1000,doc="inclusive upper bound")

    def __call__(self):
        super(UniformRandomInt, self).__call__()
        x = self.random_generator.randint(self.lbound,self.ubound)
        return x


class Choice(RandomDistribution):
    """
    Return a random element from the specified list of choices.

    Accepts items of any type, though they are typically numbers.
    See the choice() function in the random module for further details.
    """
    choices = param.List(default=[0,1],
        doc="List of items from which to select.")

    def __call__(self):
        super(Choice, self).__call__()
        return self.random_generator.choice(self.choices)


class NormalRandom(RandomDistribution):
    """
    Normally distributed (Gaussian) random number.

    Specified with mean mu and standard deviation sigma.
    See the random module for further details.
    """
    mu = param.Number(default=0.0,doc="Mean value.")
    sigma = param.Number(default=1.0,doc="Standard deviation.")

    def __call__(self):
        super(NormalRandom, self).__call__()
        return self.random_generator.normalvariate(self.mu,self.sigma)


class VonMisesRandom(RandomDistribution):
    """
    Circularly normal distributed random number.

    If kappa is zero, this distribution reduces to a uniform random
    angle over the range 0 to 2*pi.  Otherwise, it is concentrated to
    a greater or lesser degree (determined by kappa) around the mean
    mu.  For large kappa (narrow peaks), this distribution approaches
    the Gaussian (normal) distribution with variance 1/kappa.  See the
    random module for further details.
    """

    mu = param.Number(default=0.0,softbounds=(0.0,2*pi),doc="""
        Mean value, in the range 0 to 2*pi.""")

    kappa = param.Number(default=1.0,softbounds=(0.0,50.0),doc="""
        Concentration (inverse variance).""")

    def __call__(self):
        super(VonMisesRandom, self).__call__()
        return self.random_generator.vonmisesvariate(self.mu,self.kappa)




class TimeFactor(NumberGenerator, TimeDependentValue):
    """
    The current time multiplied by some conversion factor.
    """

    factor = param.Number(default=1.0, doc="""
       The factor multiplied with the current time value.""")

    def __call__(self):
        return self.time_fn() * self.factor



class BoxCar(NumberGenerator, TimeDependentValue):
    """
    The boxcar function over the specified time interval. The bounds
    are exclusive: zero is returned at the onset time and at the
    offset (onset+duration).

    If duration is None, then this reduces to a step function around the
    onset value with no offset.

    See http://en.wikipedia.org/wiki/Boxcar_function
    """

    onset = param.Number(0.0, doc="Time of onset.")

    duration = param.Number(None, allow_None=True,  doc="Duration of step value.")

    def __call__(self):
        if self.time_fn() <= self.onset:
            return 0.0
        elif (self.duration is not None) and (self.time_fn() > self.onset + self.duration):
            return 0.0
        else:
            return 1.0



class SquareWave(NumberGenerator, TimeDependentValue):
    """
    Generate a square wave with 'on' periods returning 1.0 and
    'off'periods returning 0.0 of specified duration(s). By default
    the portion of time spent in the high state matches the time spent
    in the low state.

    The 'on' state begins after a time specified by the 'onset'
    parameter.  The onset duration supplied must be less than the off
    duration.
    """

    onset = param.Number(0.0, doc="""Time of onset of the first 'on'
        state relative to time 0. Must be set to a value less than the
        'off_duration' parameter.""")

    duration = param.Number(1.0, allow_None=False, doc="""
         Duration of the 'on' state during which a value of 1.0 is
         returned.""")

    off_duration = param.Number(default=None, allow_None=True, doc="""
        Duration of the 'off' value state during which a value of 0.0
        is returned. By default, this duration matches the value of
        the 'duration' parameter.""")

    def __init__(self, **params):
        super(SquareWave,self).__init__(**params)

        if self.off_duration is None:
            self.off_duration = self.duration

        if self.onset > self.off_duration:
            raise AssertionError("Onset value needs to be less than %s" % self.onset)

    def __call__(self):
        phase_offset = (self.time_fn() - self.onset) % (self.duration + self.off_duration)
        if phase_offset < self.duration:
            return 1.0
        else:
            return 0.0



class ExponentialDecay(NumberGenerator, TimeDependentValue):
    """
    Function object that provides a value that decays according to an
    exponential function, based on a given time function.

    Returns starting_value*base^(-time/time_constant).

    See http://en.wikipedia.org/wiki/Exponential_decay.
    """
    starting_value = param.Number(1.0, doc="Value used for time zero.")
    ending_value = param.Number(0.0, doc="Value used for time infinity.")

    time_constant = param.Number(10000,doc="""
        Time scale for the exponential; large values give slow decay.""")

    base = param.Number(e, doc="""
        Base of the exponent; the default yields starting_value*exp(-t/time_constant).
        Another popular choice of base is 2, which allows the
        time_constant to be interpreted as a half-life.""")

    def __call__(self):
        Vi = self.starting_value
        Vm = self.ending_value
        return Vm + (Vi - Vm) * self.base**(-1.0*float(self.time_fn())/
                                                 float(self.time_constant))


class BoundedNumber(NumberGenerator):
    """
    Function object that silently enforces numeric bounds on values
    returned by a callable object.
    """
    generator = param.Callable(None, doc="Object to call to generate values.")

    bounds = param.Parameter((None,None), doc="""
        Legal range for the value returned, as a pair.

        The default bounds are (None,None), meaning there are actually
        no bounds.  One or both bounds can be set by specifying a
        value.  For instance, bounds=(None,10) means there is no lower
        bound, and an upper bound of 10.""")

    def __call__(self):
        val = self.generator()
        min_, max_ = self.bounds
        if   min_ != None and val < min_: return min_
        elif max_ != None and val > max_: return max_
        else: return val


_public = list(set([_k for _k,_v in locals().items() if isinstance(_v,type) and issubclass(_v,NumberGenerator)]))
__all__ = _public
