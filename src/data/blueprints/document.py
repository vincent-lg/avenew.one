# Copyright (c) 2020, LE GOFF Vincent
# All rights reserved.

# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:

# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.

# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.

# 3. Neither the name of the copyright holder nor the names of its
#    contributors may be used to endorse or promote products derived from
#    this software without specific prior written permission.

# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS
# BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY,
# OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED
# OF THE POSSIBILITY OF SUCH DAMAGE.

"""Blueprint document.

A document is a set of data in a certain format, describing
a single object that should be either created or updated in the database.
Blueprints in TalisMUD are written in YML, and a document should be in
this format.  However, the document structure is flexible enough,
so you could connect it to a different parser which uses JSON or
something similar.

Document can be extended depending on their type.  For instance, the room
document will be generated automatically depending on the data
entity (PonyORM entity).  However, one can replace such a definition
to handle user customization.

"""

from importlib import import_module
from typing import Any, Dict, Optional

from data.base import db

NOT_SET = object()
DOCUMENT_TYPES = {
        "room": "data.blueprints.room.RoomDocument",
}

class Document:

    """
    Base class for documents, regardless of the used format.

    Documents in the context of blueprints should be fed as
    dictionaries.  This allows to add other parsers (the initial parser
    being YML).  You can send a document to be parsed in a simple
    way:

        >>> from data.blueprints import select
        >>> doc = select({
        ...     "type": "room",
        ...     "barcode": "begin",
        ...     "x": 0,
        ...     "y": 0,
        ...     "z": 0,
        ...     "title": "My first room",
        ...     "description": "This is my first room.  Cool huh?",
        ...     "exits": {
        ...             "north": {
        ...                     "to": "next",
        ...                     "back": "south",
        ...             }, # ... other exits perhaps
        ...      }, # ... other room fields perhaps
        ... })
        >>> doc
        <RoomDocument>
        >>> doc.apply() # Create the room, or update it

    The only field that is truly mandatory is "type".  It will influence
    whatever document type is returned (an instance of Document
    or its children classes).  The document type will influence
    what other fields are expected.  The order of field doesn't matter.
    However, some fields are mandatory.  Some are optional.
    Fields have a fixed type although some degree of conversion
    is available.  To better understand the mechanism, look at
    a concrete document type, like `RoomDescription`.

    Methods available on all document types:
        apply(): apply this document in the database directly.

    """

    fields = {}

    def __init__(self):
        self.cleaned = Namespace()

    def fill(self, document: Dict[str, Any],
            section: Optional[Dict[str, Any]] = None):
        """
        Fill the cleaned document with the specified dictionary.

        Args:
            document (dict): the document as a dictionary.
            section (dict, optional): the section if analyzing
                    a subset of document.

        """
        section = section or type(self).fields
        for key, definition in section.items():
            def_type = definition.pop("type", None)
            if def_type is None:
                raise ValueError("the definition of {key!r} has no type")

            method_name = f"is_proper_{def_type}"
            value = document.get(key, NOT_SET)
            method = getattr(self, method_name, None)
            if method is None:
                raise ValueError(f"no {method_name} method")

            ok = method(value, document, **definition)
            if ok is not NOT_SET:
                setattr(self.cleaned, key, ok)
            else:
                value = getattr(self, f"default_{def_type}")()
                setattr(self.cleaned, key, value)

    def is_proper_str(self, value, document, max_len=None,
            presence="required"):
        """Parse a simple string."""
        if presence == "required":
            if value is NOT_SET:
                raise ValueError("this field is required")
            return value
        elif presence == "optional":
            return value

        raise ValueError(f"presence {presence} not known")

    def default_str(self):
        return ""

    def default_int(self):
        return 0

    def is_proper_int(self, value, document, presence="required"):
        """Parse an integer."""
        if presence == "required":
            if value is NOT_SET:
                raise ValueError("this field is required")

        if value is not NOT_SET:
            try:
                ok = int(value)
            except ValueError:
                raise ValueError(f"value {value} isn't correct")
        else:
            ok = value

        if presence in ("required", "optional"):
            return ok

        raise ValueError(f"presence {presence} not known")


def create(document: Dict[str, Any]):
    """
    Create a document of the specified type.

    Args:
        document (dict): the document as a dictionary.

    Note: the dictionary should at least have a field named "type",
    containing the document type.

    """
    # document['type'] is mandatory
    document_type = document.pop("type", None)
    if document_type is None:
        raise ValueError("the given document doesn't have a field 'type', describing the document type")

    document_type = document_type.lower()
    if document_type not in DOCUMENT_TYPES:
        raise ValueError(f"the specified document type, {document_type!r}, isn't a valid document type")

    document_module, document_class = DOCUMENT_TYPES[
            document_type].rsplit(".", 1)
    module = import_module(document_module)
    DocClass = getattr(module, document_class, None)
    if DocClass is None:
        raise ValueError(f"cannot find the class {document_class} in {document_module}")

    doc = DocClass()
    doc.fill(document)
    return doc

class Namespace:

    pass
