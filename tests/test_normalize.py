def test_t14_normalization_units():
    from fltrial.normalize import is_no_observation, normalize

    assert normalize("  Cotton ", "text") == normalize("cotton", "text") == "cotton"
    assert normalize("Studio \t  Bowl", "text") == "studio bowl"
    assert normalize("Studio\u00a0Bowl", "text") == "studio bowl"
    assert normalize("\uff23otton", "text") == "cotton"

    assert normalize("2", "int") == normalize("2.0", "int") == normalize(" 2 ", "int")
    assert normalize("2", "int") != normalize("1", "int")

    assert normalize("Navy", "text") != normalize("Blue", "text")

    for value in ("UNKNOWN", "", "None", None, "   "):
        assert is_no_observation(value), repr(value)
    for value in ("Blue", "0", "Studio Bowl"):
        assert not is_no_observation(value), repr(value)
