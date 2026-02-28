def normalize_filament_usage(presets, usage):
    """
    Fixes cases where purge-line filament shows <1g usage.
    Adds that usage to the largest filament entry.
    """

    if not presets or not usage:
        return presets or [], usage or []

    # Find the index of the largest usage
    max_index = usage.index(max(usage))

    # Add all <1g values to the largest filament
    for i, grams in enumerate(usage):
        if grams < 1 and i != max_index:
            usage[max_index] += grams
            usage[i] = 0

    return presets, usage
