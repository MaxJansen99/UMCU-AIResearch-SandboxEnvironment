from typing import Any, Callable


FilterOperator = Callable[[Any, Any], bool]
FilterSpec = tuple[str, str, Any]


def _contains(actual: Any, expected: Any) -> bool:
    return actual is not None and expected is not None and str(expected) in str(actual)


def _startswith(actual: Any, expected: Any) -> bool:
    return actual is not None and expected is not None and str(actual).startswith(str(expected))


def _endswith(actual: Any, expected: Any) -> bool:
    return actual is not None and expected is not None and str(actual).endswith(str(expected))


def _in(actual: Any, expected: Any) -> bool:
    return actual is not None and expected is not None and actual in expected


def _not_in(actual: Any, expected: Any) -> bool:
    return actual is not None and expected is not None and actual not in expected


def _date_in_ranges(actual: Any, expected: Any) -> bool:
    if actual is None or not isinstance(expected, list):
        return False

    actual_value = str(actual)
    if len(actual_value) != 8 or not actual_value.isdigit():
        return False

    for date_range in expected:
        if not isinstance(date_range, dict):
            continue
        min_value = date_range.get("min")
        max_value = date_range.get("max")
        if min_value is not None and actual_value < str(min_value):
            continue
        if max_value is not None and actual_value > str(max_value):
            continue
        return True

    return False


OPERATORS: dict[str, FilterOperator] = {
    "==": lambda actual, expected: actual == expected,
    "!=": lambda actual, expected: actual != expected,
    ">": lambda actual, expected: actual is not None and expected is not None and actual > expected,
    ">=": lambda actual, expected: actual is not None and expected is not None and actual >= expected,
    "<": lambda actual, expected: actual is not None and expected is not None and actual < expected,
    "<=": lambda actual, expected: actual is not None and expected is not None and actual <= expected,
    "contains": _contains,
    "startswith": _startswith,
    "endswith": _endswith,
    "in": _in,
    "not in": _not_in,
    "date in ranges": _date_in_ranges,
    "is None": lambda actual, _: actual is None,
    "not None": lambda actual, _: actual is not None,
}


HIDDEN_TAGS = {
    "",
    "SOPInstanceUID",
    "InstanceNumber",
    "CodingSchemeIdentificationSequence",
    "ContributingEquipmentSequence",
    "DimensionOrganizationSequence",
    "DimensionIndexSequence",
    "NumberOfFrames",
    "ImagePositionPatient",
    "PixelSpacing",
    "TotalPixelMatrixOriginSequence",
    "OpticalPathSequence",
    "SpecimenDescriptionSequence",
    "SharedFunctionalGroupsSequence",
    "PerFrameFunctionalGroupsSequence",
    "PatientIdentityRemoved",
    "DeidentificationMethod",
    "DeidentificationMethodCodeSequence",
    "ImageOrientationPatient",
    "PatientName",
    "AccessionNumber",
    "ReferringPhysicianName",
}

ALLOWED_TAGS = [
    "Modality",
    "PatientBirthDate",
    "BodyPartExamined",
    "PatientSex",
]


def normalize_filter_specs(raw_filters: list[Any]) -> list[FilterSpec]:
    normalized: list[FilterSpec] = []
    for raw_filter in raw_filters:
        if not isinstance(raw_filter, (list, tuple)) or len(raw_filter) != 3:
            raise ValueError("Each filter must be [tag_name, operator, value].")

        tag_name, operator_name, expected = raw_filter
        if not isinstance(tag_name, str) or not tag_name:
            raise ValueError("Filter tag_name must be a non-empty string.")
        if not isinstance(operator_name, str) or operator_name not in OPERATORS:
            raise ValueError(f"Unsupported operator: {operator_name}. Supported operators: {sorted(OPERATORS)}")

        normalized.append((tag_name, operator_name, expected))
    return normalized
