__author__ = "Anders Logg (logg@simula.no)"
__date__ = "2004-10-04 -- 2007-03-20"
__copyright__ = "Copyright (C) 2004-2007 Anders Logg"
__license__  = "GNU GPL Version 2"

# Modified by Garth N. Wells 2006
# Modified by Marie E. Rognes 2006
# Modified by Andy R Terrel 2007

# Python modules
import sys

# FIAT modules
from FIAT.shapes import *
from FIAT.Lagrange import Lagrange, VectorLagrange
from FIAT.DiscontinuousLagrange import DiscontinuousLagrange, DiscontinuousVectorLagrange
from FIAT.CrouzeixRaviart import CrouzeixRaviart, VectorCrouzeixRaviart 
from FIAT.RaviartThomas import RaviartThomas
from FIAT.BDM import BDM
from FIAT.Nedelec import Nedelec

# FFC common modules
from ffc.common.debug import *

# FFC fem modules
from mapping import *
import mixedelement

shape_to_string = {LINE: "line", TRIANGLE: "triangle", TETRAHEDRON: "tetrahedron"}
string_to_shape = {"line": LINE, "triangle": TRIANGLE, "tetrahedron": TETRAHEDRON}

class FiniteElement:
    """A FiniteElement represents a finite element in the classical
    sense as defined by Ciarlet. The actual work is done by FIAT and
    this class serves as the interface to FIAT finite elements from
    within FFC.

    A FiniteElement is specified by giving the family and degree of the
    finite element, together with the name of the reference cell:

      family: "Lagrange", "Hermite", ...
      shape:  "line", "triangle", "tetrahedron"
      degree: 0, 1, 2, ...

    The shape and degree must match the chosen family of finite element.
    """

    def __init__(self, family, shape, degree = None, num_components = None):
        "Create FiniteElement."

        # Save element family
        self.__family = family

        # Get FIAT shape from string
        self.__fiat_shape = string_to_shape[shape]

        # Get FIAT element from string
        (self.__fiat_element, self.__mapping) = self.__choose_element(family, shape, degree, num_components)

        # Get entity dofs from FIAT element
        self.__entity_dofs = self.__fiat_element.dual_basis().entity_ids

        # Repeat entity dofs for tensor product elements
        num_reps = self.__fiat_element.dual_basis().num_reps
        if num_reps > 1:
            self.__entity_dofs = [self.__entity_dofs for i in range(num_reps)]

    def signature(self):
        "Return a string identifying the finite element"
        if self.vectordim() > 1:
            return "%s finite element of degree %d on a %s with %d components" % \
                   (self.__family, self.degree(), shape_to_string[self.__fiat_shape], self.vectordim())
        else:
            return "%s finite element of degree %d on a %s" % \
                   (self.__family, self.degree(), shape_to_string[self.__fiat_shape])

    def basis(self):
        "Return basis of finite element space"
        return self.__fiat_element.function_space()

    def degree(self):
        "Return degree of polynomial basis"
        return self.basis().degree()

    def cell_shape(self):
        "Return the cell shape"
        return self.__fiat_element.domain_shape()

    def facet_shape(self):
        "Return shape of facet"
        return self.cell_shape() - 1

    def space_dimension(self):
        "Return the dimension of the finite element function space"
        return len(self.basis())

    def cell_dimension(self):
        "Return dimension of shape"
        return dim[self.cell_shape()]

    def value_rank(self):
        "Return the rank of the value space"
        return self.basis().rank()
    
    def value_dimension(self, i):
        "Return the dimension of the value space for axis i"
        if self.value_rank() == 0:
            return 1
        else:
            return self.basis().tensor_dim()[i]

    def num_sub_elements(self):
        "Return the number of sub elements"
        return 1

    def sub_element(self, i):
        "Return sub element i"
        return self

    def vectordim(self):
        "Return vector dimension (number of components)"
        if self.value_rank() == 0:
            return 1
        elif self.value_rank() == 1:
            return self.value_dimension(0)
        else:
            raise RuntimeError, "Can only handle scalar or vector-valued elements."

    def num_facets(self):
        "Return number of facets for shape of element."
        if self.__fiat_element.domain_shape() == TRIANGLE:
            return 3
        elif self.__fiat_element.domain_shape() == TETRAHEDRON:
            return 4
        else:
            raise RuntimeError, "Unknown shape."

    def mapping(self):
        "Return the type of mapping associated with the element"
        return self.__mapping

    def tabulate(self, order, points, facet = None):
        """Return tabulated values of derivatives up to given order of
        basis functions at given points. If facet is not None, then the
        values are tabulated on the given facet, with the points given
        on the corresponding reference facet."""
        if facet == None:
            return self.__fiat_element.function_space().tabulate_jet(order, points)
        else:
            facet_shape = self.facet_shape()
            return self.__fiat_element.function_space().trace_tabulate_jet(facet_shape, facet, order, points)

    def entity_dofs(self):
        """Return a dictionary mapping the mesh entities of the
        reference cell to the degrees of freedom associated with
        the entity"""
        return self.__entity_dofs

    def __add__(self, other):
        "Create mixed element."
        if isinstance(other, FiniteElement):
            return mixedelement.MixedElement([self, other])
        elif isinstance(other, mixedelement.MixedElement):
            return mixedelement.MixedElement([self] + other.elements)
        else:
            raise RuntimeError, "Unable to create mixed element from given object: " + str(other)

    def __choose_element(self, family, shape, degree, num_components):
        "Choose FIAT finite element from string"
    
        # Choose FIAT function space
        if family == "Lagrange":
            return (Lagrange(self.__fiat_shape, degree),
                    Mapping.AFFINE)

        if family == "Vector Lagrange":
            return (VectorLagrange(self.__fiat_shape, degree, num_components),
                    Mapping.AFFINE)

        if family == "Discontinuous Lagrange":
            return (DiscontinuousLagrange(self.__fiat_shape, degree),
                    Mapping.AFFINE)

        if family == "Discontinuous vector Lagrange":
            return (DiscontinuousVectorLagrange(self.__fiat_shape, degree, num_components),
                    Mapping.AFFINE)

        if family == "Crouzeix-Raviart":
            return (CrouzeixRaviart(self.__fiat_shape),
                    Mapping.AFFINE)

        if family == "Vector Crouzeix-Raviart":
            return (VectorCrouzeixRaviart(self.__fiat_shape),
                    Mapping.AFFINE)

        if family == "Raviart-Thomas" or family == "RT":
            print "Warning: element untested"
            return (RaviartThomas(self.__fiat_shape, degree),
                    Mapping.PIOLA)

        if family == "Brezzi-Douglas-Marini" or family == "BDM":
            print "Warning: element untested"
            return (BDM(self.__fiat_shape, degree),
                    Mapping.PIOLA)

        if family == "Nedelec":
            print "Warning: element untested"
            return (Nedelec(degree),
                    Mapping.PIOLA) # ?

        # Unknown element
        raise RuntimeError, "Unknown finite element: " + str(family)

    def __repr__(self):
        "Pretty print"
        return self.signature()
