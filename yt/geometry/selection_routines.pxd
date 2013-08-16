"""
Geometry selection routine imports.

Author: Matthew Turk <matthewturk@gmail.com>
Affiliation: Columbia University
Homepage: http://yt.enzotools.org/
License:
  Copyright (C) 2011 Matthew Turk.  All Rights Reserved.

  This file is part of yt.

  yt is free software; you can redistribute it and/or modify
  it under the terms of the GNU General Public License as published by
  the Free Software Foundation; either version 3 of the License, or
  (at your option) any later version.

  This program is distributed in the hope that it will be useful,
  but WITHOUT ANY WARRANTY; without even the implied warranty of
  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
  GNU General Public License for more details.

  You should have received a copy of the GNU General Public License
  along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

cimport numpy as np
from oct_visitors cimport Oct, OctVisitorData, \
    oct_visitor_function

cdef class SelectorObject:
    cdef public np.int32_t min_level
    cdef public np.int32_t max_level
    cdef int overlap_cells
    cdef np.float64_t domain_width[3]
    cdef bint periodicity[3]

    cdef void recursively_visit_octs(self, Oct *root,
                        np.float64_t pos[3], np.float64_t dds[3],
                        int level,
                        oct_visitor_function *func,
                        OctVisitorData *data,
                        int visit_covered = ?)
    cdef int select_grid(self, np.float64_t left_edge[3],
                               np.float64_t right_edge[3],
                               np.int32_t level, Oct *o = ?) nogil
    cdef int select_cell(self, np.float64_t pos[3], np.float64_t dds[3]) nogil

    cdef int select_point(self, np.float64_t pos[3]) nogil
    cdef int select_sphere(self, np.float64_t pos[3], np.float64_t radius) nogil
    cdef int select_bbox(self, np.float64_t left_edge[3],
                               np.float64_t right_edge[3]) nogil

    # compute periodic distance (if periodicity set) assuming 0->domain_width[i] coordinates
    cdef np.float64_t difference(self, np.float64_t x1, np.float64_t x2, int d) nogil
