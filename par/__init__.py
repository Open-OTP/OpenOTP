import builtins
from .parparser import parse_par_file

builtins.config = parse_par_file('local.par')
