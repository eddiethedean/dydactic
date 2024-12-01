import pydantic


Record = dict | pydantic.BaseModel
Json = str | bytes | bytearray