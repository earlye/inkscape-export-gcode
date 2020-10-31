def float_range(start, stop, step, includeStop = False):
    if start < stop:
        while start < stop:
            yield float(start)
            start += step
    else:
        while start > stop:
            yield float(start)
            start += step
    if includeStop:
        yield stop
