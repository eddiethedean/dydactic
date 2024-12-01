import typing
from datetime import datetime
import types

import dateutil.parser


def cast_as(value: typing.Any, annotation: type) -> typing.Any:
    if isinstance(value, annotation):
        return value
    if annotation is datetime:
        return dateutil.parser.parse(value)
    return annotation(value)
    

def cast_as_union(
    value: typing.Any,
    ut: typing._UnionGenericAlias | types.UnionType
) -> typing.Any:
    for _type in ut.__args__:
        try:
            return cast_as(value, _type)
        except:
            ...
    raise TypeError('Failed to cast value')


def cls_annotations(cls) -> dict[str, type]:
    return cls.__dict__['__annotations__']


def cast_as_annotation(
    value: typing.Any,
    annotation: type
) -> typing.Any:
    if isinstance(annotation, (typing._UnionGenericAlias, types.UnionType)):
        return cast_as_union(value, annotation)
    return cast_as(value, annotation)


class ValidationError(ValueError):
    ...


Class = typing.TypeVar('Class', bound=typing.Callable)


def cast_to_annotated_class(d: dict[str, typing.Any], cls: Class) -> Class:
    annotations: dict[str, type] = cls_annotations(cls)
    new_data: dict[str, typing.Any] = d.copy()
    errors: dict[str, dict] = {}
    for key, value in new_data.items():
        annotation: type = annotations[key]
        try:
            new_data[key] = cast_as_annotation(value, annotations[key])
        except:
            errors[key] = {
                'type': annotation,
                'input_value':value,
                'input_type': type(value)
            }
    if errors:
        raise ValidationError(errors)
    return cls(**new_data)