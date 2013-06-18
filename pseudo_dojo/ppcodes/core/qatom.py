from __future__ import division, print_function

import os
import collections
import numpy as np

from pseudo_dojo.ppcodes.nist import nist_database

from scipy.interpolate import UnivariateSpline

__version__ = "0.1"
__status__ = "Development"
__date__ = "$April 26, 2013M$"

__all__ = [
    "QState",
    "AtomicConfiguration",
    "RadialFunction",
    "RadialWaveFunction",
    "plot_aepp",
    "plot_logders",
    "Dipole",
]

##########################################################################################
# Helper functions

_char2l = {
    "s": 0,
    "p": 1,
    "d": 2,
    "f": 3,
    "g": 4,
    "h": 5,
    "i": 6,
}


def _asl(obj):
    try:
        return _char2l[obj]
    except KeyError:
        return int(obj)


def states_from_string(confstr):
    states = []
    tokens = confstr.split()

    if tokens[0].startswith("["):
        noble_gas = AtomicConfiguration.neutral_from_symbol(tokens.pop(0)[1:-1])
        states = noble_gas.states
                                                                      
    states.extend(parse_orbtoken(t) for t in tokens)
    return states


def parse_orbtoken(orbtoken):
    import re
    m = re.match("(\d+)([spdfghi]+)(\d+)", orbtoken.strip())
    if m:
        return QState(n=m.group(1), l=m.group(2), occ=m.group(3))

    raise ValueError("Don't know how to interpret %s" % str(orbtoken))

##########################################################################################


class QState(collections.namedtuple("QState", "n, l, occ, eig, j, s")):
    "Quantum numbers, occupancies and eigenvalue of the atomic orbital."
    # TODO
    #Spin +1, -1 or 1,2 or 0,1?

    def __new__(cls, n, l, occ, eig=None, j=None, s=None):
        "Intercepts super.__new__ adding type conversion and default values"
        eig = float(eig) if eig is not None else eig
        j = int(j) if j is not None else j
        s = int(s) if s is not None else s
        return super(QState, cls).__new__(cls, int(n), _asl(l), float(occ), eig=eig, j=j, s=s)

    #@classmethod
    #def asqstate(cls, obj):
    #    if isinstance(obj, cls):
    #        return obj
    #    #if isinstance(obj, str):
    #    raise ValueError("Dont' know how to cast %s: %s" % (obj.__class__.__name__, obj))

    # Rich comparison support. 
    # Note that the ordering is based on the quantum numbers and not on energies!

    #def __gt__(self, other):
    #    if self.has_j:
    #        raise NotImplementedError("")
    #    if self.n != other.n: return self.n > other.n
    #    if self.l != other.l

    #    if self == other:
    #        return False
    #    else:
    #        raise RuntimeError("Don't know how to compare %s with %s" % (self, other))

    #def __lt__(self, other):

    #@property
    #def has_j(self):
    #    return self.j is not None

    #@property
    #def has_s(self):
    #    return self.s is not None

    @property
    def to_dict(self):
        d = {k: v for (k,v) in self._asdict().items() if v is not None}
        d["@module"] = self.__class__.__module__
        d["@class"] = self.__class__.__name__
        return d

    @classmethod
    def from_dict(cls, d):
        return cls(**d)

    def to_apeinput(self):
        if self.s is None:
            string = "%s | %s | %s " % (self.n, self.l, self.occ)
        elif self.s == 2:
            raise NotImplementedError("Spin")
        elif self.j is not None:
            raise NotImplementedError("Spinor")
        else:
            raise ValueError("Don't know how to convert %s" % self)

        return [string,]

##########################################################################################


class AtomicConfiguration(object):
    """Atomic configuration defining the AE atom."""

    def __init__(self, Z, states):
        """
        Args:
            Z:
                Atomic number.
            states:
                List of QState instances.
        """
        self.Z = Z
        self.states = states

    @classmethod
    def from_string(cls, Z, string, has_s=False, has_j=False):
        if not has_s and not has_j:
            # Ex: [He] 2s2 2p3
            states = states_from_string(string)
        else:
            raise NotImplementedError("")

        return cls(Z, states)

    def __str__(self):
        lines = ["%s: " % self.Z]
        lines += [str(state) for state in self]
        return "\n".join(lines)
                                                
    def __iter__(self):
        return self.states.__iter__()

    def __eq__(self, other):
        if len(self.states) != len(other.states):
            return False

        return (self.Z == other.Z and
                all(s1 == s2 for s1, s2 in zip(self.states, other.states)))

    def __ne__(self, other): 
        return not self == other

    @classmethod
    def neutral_from_symbol(cls, symbol):
        """
        symbol: str or int
            Can be a chemical symbol (str) or an atomic number (int).
        """
        entry = nist_database.get_neutral_entry(symbol)
        states = [QState(n=s[0], l=s[1], occ=s[2]) for s in entry.states]
        return cls(entry.Z, states)

    def copy(self):
        """Shallow copy of self."""
        return AtomicConfiguration(self.Z, [s for s in self.states])

    @property
    def symbol(self):
        return nist_database.symbol_from_Z(self.Z)

    @property
    def spin_mode(self):
        """
        unpolarized: Spin-unpolarized calculation.
        polarized: Spin-polarized calculation.
        """
        for state in self:
            # FIXME
            if state.s is not None and state.s == 2:
                return "polarized"
        return "unpolarized"

    @property
    def echarge(self):
        """Electronic charge (float <0)"""
        return -sum(state.occ for state in self)

    @property
    def isneutral(self):
        """True if neutral configuration."""
        return abs(self.echarge + self.Z) < 1.e-8

    def add_state(self, **qnumbers):
        """Add a quantum state to self."""
        self._push(QState(**qnumbers))

    def remove_state(self, **qnumbers):
        """Remove a quantum state from self."""
        self._pop(QState(**qnumbers))

    def _push(self, state):
        # TODO check that ordering in the input does not matter!
        if state in self.states:
            raise ValueError("state %s is already in self" % str(state))
        self.states.append(state)

    def _pop(self, state):
        try:
            self.states.remove(state)
        except ValueError:
            raise

    #@property
    #def num_nodes(self):
    #    "Exact number of nodes computed from the quantum numbers."

    @property
    def to_dict(self):
        """Json-serializable dict representation."""
        return {
            "Z"      : self.Z,
            "states" : self.states,
            "@class" : self.__class__.__name__,
            "@module": self.__class__.__name__,
        }

    @classmethod
    def from_dict(cls, d):
        """Reconstitute the object from a dict representation  created using to_dict."""
        return cls(d["Z"], d["states"])

#class SpinPolarizedConfiguration(AeAtom):
#class DiracConfiguration(AeAtom):

##########################################################################################


class RadialFunction(object):
    """A RadialFunction has a name, a radial mesh and values defined on this mesh."""

    def __init__(self, name, rmesh, values):
        """
        Args:
            name:
                Name of the function (string).
            rmesh:
                Iterable with the points of the radial mesh. 
            values:
                Iterable with the values of the function on the radial mesh.
        """
        self.name = name 
        self.rmesh = np.ascontiguousarray(rmesh)
        self.values = np.ascontiguousarray(values)

        assert len(self.rmesh) == len(self.values)

    def __len__(self):
        return len(self.values)

    def __iter__(self):
        "Iterate over (rpoint, value)"
        return iter(zip(self.rmesh, self.values))

    def __getitem__(self, rslice):
        return self.rmesh[rslice], self.values[rslice]

    def __str__(self):
        return "<%s, name = %s>" % (self.__class__.__name__, self.name)

    #def __add__(self):
    #def __sub__(self):
    #def __mul__(self):

    @classmethod
    def from_filename(cls, filename, rfunc_name=None, cols=(0,1)):
        """
        Initialize the object by reading data from filename (txt format)

        Args:
            filename:
                Path to the file containing data.
            rfunc_name:
                Optional name for the RadialFunction (defaults to filename)
            cols:
                List with the index of the columns containing the radial mesh and the values.
        """
        data = np.loadtxt(filename)
        rmesh, values = data[:,cols[0]], data[:,cols[1]]
        name = filename if rfunc_name is None else rfunc_name
        return cls(name, rmesh, values)

    @property
    def rmax(self):
        """Outermost point of the radial mesh."""
        return self.rmesh[-1]

    @property
    def rsize(self):
        """Size of the radial mesh."""
        return len(self.rmesh)

    @property
    def minmax_ridx(self): 
        """
        Returns the indices of the values in a list with the maximum and minimum value.
        """
        minimum = min(enumerate(self.values), key=lambda s: s[1]) 
        maximum = max(enumerate(self.values), key=lambda s: s[1]) 
        return minimum[0], maximum[0]

    @property
    def inodes(self):
        inodes = []
        for i in range(len(self.values)-1):
            if self.values[i] * self.values[i+1] <= 0:
                inodes.append(i)
        return inodes

    @property
    def spline(self):
        """Cubic spline."""
        try:
            return self._spline
        except AttributeError:
            self._spline = UnivariateSpline(self.rmesh, self.values, s=0)
            return self._spline

    @property
    def roots(self):
        """Return the zeros of the spline."""
        return self.spline.roots()

    def derivatives(self, r):
        """Return all derivatives of the spline at the point r."""
        return self.spline.derivatives(r)

    def integral(self, a=None, b=None):
        """
        Return definite integral of the spline of (r**2 values**2) between two given points a and b

        Args:
            a:
                First point. rmesh[0] if a is None
            b:
                Last point. rmesh[-1] if a is None
        """
        a = self.rmesh[0] if a is None else a
        b = self.rmesh[-1] if b is None else b
        r2v2_spline = UnivariateSpline(self.rmesh, (self.rmesh * self.values) ** 2, s=0)
        return r2v2_spline.integral(a, b)

    #@property
    #def peaks(self):

    def ifromr(self, rpoint):
        """The index of the point."""
        for (i, r) in enumerate(self.rmesh):
            if r > rpoint: 
                return i-1

        if (rpoint == self.rmesh[-1]):
            return len(self.rmesh)
        else:
            raise ValueError("Cannot find %s in rmesh" % rpoint)

    def ir_small(self, abs_tol=0.01):
        """
        Returns the rightmost index where the abs value of the wf becomes greater than abs_tol 

        Args:
            abs_tol:
                Absolute tolerance.

        .. warning:
            Assumes that self.values are tending to zero for r --> infinity.
        """
        for i in range(len(self.rmesh)-1, -1, -1):
            if abs(self.values[i]) > abs_tol:
                break
        return i

##########################################################################################

class RadialWaveFunction(RadialFunction):
    TOL_BOUND = 1.e-10

    def __init__(self, state, name, rmesh, values):
        super(RadialWaveFunction, self).__init__(name, rmesh, values)
        self.state = state

    @property
    def isbound(self):
        """True if self is a bound state."""
        back = min(10, len(self))
        return all(abs(self.values[-back:]) < self.TOL_BOUND)

#class DiracWaveFunction(RadialFunction):

##########################################################################################

def plot_aepp(ae_funcs, pp_funcs=None, rmax=None, title=None, show=True, savefig=None, **kwargs): 
    """
    Uses Matplotlib to plot the radial wavefunction (AE only or AE vs PP)

    Args:
        ae_funcs:
            All-electron radial functions.
        pp_funcs:
            Pseudo radial functions.
        rmax:
            float or dictionary {state: rmax} where rmax is the maximum r (Bohr) that will be be plotted. 
        title: 
            string with the title of the plot.
        show:
            True to show the figure
        savefig:
            'abc.png' or 'abc.eps'* to save the figure to a file.
        **kwargs:
            keywords arguments passed to matplotlib.
    """
    import matplotlib.pyplot as plt
    fig = plt.figure()

    num_funcs = len(ae_funcs) if pp_funcs is None else len(pp_funcs)

    spl_idx = 0
    for (state, ae_phi) in ae_funcs.items():

        if pp_funcs is not None and state not in pp_funcs:
            continue
        
        spl_idx += 1
        ax = fig.add_subplot(num_funcs, 1, spl_idx)

        if spl_idx==1 and title: 
            ax.set_title(title)

        lines, legends = [], []

        if rmax is None:
            ir = len(ae_phi) + 1 
        else:
            try:
                rm = rmax[state] 
            except TypeError:
                rm = float(rmax)

            ir = ae_phi.ifromr(rm)

        line, = ax.plot(ae_phi.rmesh[:ir], ae_phi.values[:ir], "-b", linewidth=2.0, markersize=1)

        lines.append(line)
        legends.append("AE: %s" % state)

        if pp_funcs is not None:
            pp_phi = pp_funcs[state]
            line, = ax.plot(pp_phi.rmesh[:ir], pp_phi.values[:ir], "^r", linewidth=2.0, markersize=4)
            lines.append(line)
            legends.append("PP: %s" % state)

        ax.legend(lines, legends, 'lower right', shadow=True)

        # Set yticks and labels.
        ylabel = kwargs.get("ylabel", None)
        if ylabel is not None:
            ax.set_ylabel(ylabel)

        if spl_idx == num_funcs:
            ax.set_xlabel("r [Bohr]")

        ax.grid(True)

    if show:
        plt.show()
                             
    if savefig is not None:
        fig.savefig(os.path.abspath(savefig))

##########################################################################################

def plot_logders(ae_logders, pp_logders, show=True, savefig=None): 
    """
    Uses matplotlib to plot the logarithmic derivatives.
                                                                                         
    Args:
        ae_logders:
            AE logarithmic derivatives.
        pp_logders:
            PP logarithmic derivatives.
        show:
            True to show the figure
        savefig:
            'abc.png' or 'abc.eps'* to save the figure to a file.
    """
    import matplotlib.pyplot as plt
    assert len(ae_logders) == len(pp_logders) 
    fig = plt.figure()
                                                                                         
    num_logds, spl_idx = len(ae_logders), 0

    for (state, pp_logd) in pp_logders.items():
        spl_idx += 1
        ax = fig.add_subplot(num_logds, 1, spl_idx)
                                                                                         
        lines, legends = [], []
                                                                                         
        ae_logd = ae_logders[state]

        line, = ax.plot(ae_logd.rmesh, ae_logd.values, "-b", linewidth=2.0, markersize=1)
        lines.append(line)
        legends.append("AE logder %s" % state)
                                                                                         
        line, = ax.plot(pp_logd.rmesh, pp_logd.values, "^r", linewidth=2.0, markersize=4)
        lines.append(line)
        legends.append("PP logder %s" % state)
                                                                                         
        ax.legend(lines, legends, 'lower left', shadow=True)

        if spl_idx == num_logds:
            ax.set_xlabel("Energy [Ha]")

        ax.grid(True)

    if show:
        plt.show()
                             
    if savefig is not None:
        fig.savefig(os.path.abspath(savefig))

##########################################################################################


class Dipole(object):
    """This object stores the dipole matrix elements."""
    TOL_LRULE = 0.002

    def __init__(self, istate, ostate, aeres, ppres):
        self.istate = istate
        self.ostate = ostate
        self.aeres = float(aeres)
        self.ppres = float(ppres)
        self.aempp = self.aeres - self.ppres

    @property
    def fulfills_lrule(self):
        if self.istate.lselect(self.ostate) and abs(self.aempp) > self.TOL_LRULE:
            return False
        return True

##########################################################################################