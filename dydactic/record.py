"""Type aliases for validation inputs."""

import pydantic


Record = dict | pydantic.BaseModel
"""Type alias for a record that can be validated.
    
A Record can be either a dictionary or a Pydantic BaseModel instance.
"""

Json = str | bytes | bytearray
"""Type alias for JSON data.
    
JSON can be provided as a string, bytes, or bytearray.
"""
