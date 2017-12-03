import os
import yt.utilities.fortran_utils as fpu
import glob
from yt.extern.six import add_metaclass
from yt.funcs import mylog

FIELD_HANDLERS = set()

def get_field_handlers():
    return FIELD_HANDLERS

def register_field_handler(ph):
    FIELD_HANDLERS.add(ph)


class RAMSESFieldFileHandlerRegister(type):
    """
    This is a base class that on instantiation registers the file
    handler into the list. Used as a metaclass.
    """
    def __new__(meta, name, bases, class_dict):
        cls = type.__new__(meta, name, bases, class_dict)
        if cls.ftype is not None:
            register_field_handler(cls)
        return cls


@add_metaclass(RAMSESFieldFileHandlerRegister)
class FieldFileHandler(object):
    '''
    Abstract class to handle particles in RAMSES. Each instance
    represents a single file (one domain).

    To add support to a new particle file, inherit from this class and
    implement all functions containing a `NotImplementedError`.

    See `SinkParticleFileHandler` for an example implementation.'''

    # These properties are static properties
    ftype = None  # The name to give to the particle type
    fname = None  # The name of the file(s).
    attrs = None  # The attributes of the header
    known_fields = None  # A list of tuple containing the field name and its type

    # These properties are computed dynamically
    field_offsets = None     # Mapping from field to offset in file
    field_types = None       # Mapping from field to the type of the data (float, integer, …)

    def __init__(self, ds, domain_id):
        '''
        Initalize an instance of the class. This automatically sets
        the full path to the file. This is not intended to be
        overriden in most cases.

        If you need more flexibility, rewrite this function to your
        need in the inherited class.
        '''
        self.ds = ds
        self.domain_id = domain_id
        basename = os.path.abspath(
              os.path.dirname(ds.parameter_filename))
        iout = int(
            os.path.basename(ds.parameter_filename)
            .split(".")[0].
            split("_")[1])
        icpu = domain_id

        self.fname = os.path.join(
            basename,
            self.fname.format(iout=iout, icpu=icpu))

    @property
    def exists(self):
        '''
        This function should return True if the *file* the instance
        exists. It is called for each file of the type found on the
        disk.

        By default, it just returns whether the file exists. Override
        it for more complex cases.
        '''
        return os.path.exists(self.fname)

    @classmethod
    def any_exist(cls, ds):
        '''
        This function should return True if the kind of particle
        represented by the class exists in the dataset. It takes as
        argument the class itself —not an instance— and a dataset.

        Arguments
        ---------
        * ds: a Ramses Dataset

        Note
        ----
        This function is usually called once at the initialization of
        the RAMSES Dataset structure to determine if the particle type
        (e.g. regular particles) exists.
        '''
        raise NotImplementedError

    @classmethod
    def get_field_list(cls, ds):
        raise NotImplementedError


    def read_header(self):
        '''
        This function is called once per file. It should:
        * read the header of the file and store any relevant information
        * detect the fields in the file
        * compute the offsets (location in the file) of each field

        It is in charge of setting `self.field_offsets` and `self.field_types`.
        * `field_offsets`: dictionary: tuple -> integer
           A dictionary that maps `(type, field_name)` to their
           location in the file (integer)
        * `field_types`: dictionary: tuple -> character
           A dictionary that maps `(type, field_name)` to their type
           (character), following Python's struct convention.
        '''
        raise NotImplementedError


class HydroFieldFileHandler(FieldFileHandler):
    ftype = 'ramses'
    fname = 'part_{iout:05d}.out{icpu:05d}'
    attrs = ( ('ncpu', 1, 'i'),
              ('nvar', 1, 'i'),
              ('ndim', 1, 'i'),
              ('nlevelmax', 1, 'i'),
              ('nboundary', 1, 'i'),
              ('gamma', 1, 'd'))

    @classmethod
    def any_exist(cls, ds):
        files = os.path.join(
            os.path.split(ds.parameter_filename)[0],
            'hydro_?????.out?????')
        ret = len(glob.glob(files)) > 0
        return ret

    @classmethod
    def get_field_list(cls, ds):
        num = os.path.basename(ds.parameter_filename).split("."
                )[0].split("_")[1]
        testdomain = 1 # Just pick the first domain file to read
        basename = "%s/%%s_%s.out%05i" % (
            os.path.abspath(
              os.path.dirname(ds.parameter_filename)),
            num, testdomain)
        fname = basename % "hydro"

        if not os.path.exists(fname):
            cls.fluid_field_list = []
            return

        f = open(fname, 'rb')
        attrs = cls.attrs
        hvals = fpu.read_attrs(f, attrs)

        # Store some metadata
        ds.gamma = hvals['gamma']
        nvar = cls.nvar = hvals['nvar']

        foldername  = os.path.abspath(os.path.dirname(ds.parameter_filename))
        rt_flag = any(glob.glob(os.sep.join([foldername, 'info_rt_*.txt'])))
        if rt_flag: # rt run
            if nvar < 10:
                mylog.info('Detected RAMSES-RT file WITHOUT IR trapping.')
                fields = ["Density", "x-velocity", "y-velocity", "z-velocity", "Pressure",
                          "Metallicity", "HII", "HeII", "HeIII"]
            else:
                mylog.info('Detected RAMSES-RT file WITH IR trapping.')
                fields = ["Density", "x-velocity", "y-velocity", "z-velocity", "Pres_IR",
                          "Pressure", "Metallicity", "HII", "HeII", "HeIII"]
        else:
            if nvar < 5:
                mylog.debug("nvar=%s is too small! YT doesn't currently support 1D/2D runs in RAMSES %s")
                raise ValueError
            # Basic hydro runs
            if nvar == 5:
                fields = ["Density",
                          "x-velocity", "y-velocity", "z-velocity",
                          "Pressure"]
            if nvar > 5 and nvar < 11:
                fields = ["Density",
                          "x-velocity", "y-velocity", "z-velocity",
                          "Pressure", "Metallicity"]
            # MHD runs - NOTE: THE MHD MODULE WILL SILENTLY ADD 3 TO THE NVAR IN THE MAKEFILE
            if nvar == 11:
                fields = ["Density",
                          "x-velocity", "y-velocity", "z-velocity",
                          "x-Bfield-left", "y-Bfield-left", "z-Bfield-left",
                          "x-Bfield-right", "y-Bfield-right", "z-Bfield-right",
                          "Pressure"]
            if nvar > 11:
                fields = ["Density",
                          "x-velocity", "y-velocity", "z-velocity",
                          "x-Bfield-left", "y-Bfield-left", "z-Bfield-left",
                          "x-Bfield-right", "y-Bfield-right", "z-Bfield-right",
                          "Pressure","Metallicity"]
        # Allow some wiggle room for users to add too many variables
        while len(fields) < nvar:
            fields.append("var"+str(len(fields)))
        mylog.debug("No fields specified by user; automatically setting fields array to %s", str(fields))
        cls.fluid_field_list = fields
        return fields
