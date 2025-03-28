import io
import pickle
import random
import string

import pytest
import responses

from cog_types.types import Secret, get_filename, URLFile, URLPath


def test_urlfile_protocol_validation():
    with pytest.raises(ValueError):
        URLFile("file:///etc/shadow")

    with pytest.raises(ValueError):
        URLFile("data:text/plain,hello")


def test_urlfile_custom_filename():
    u = URLFile("https://example.com/some-path", filename="my_file.txt")
    assert u.name == "my_file.txt"


@responses.activate
def test_urlfile_acts_like_response():
    responses.get(
        "https://example.com/some/url",
        json={"message": "hello world"},
        status=200,
    )

    u = URLFile("https://example.com/some/url")

    assert isinstance(u, io.IOBase)
    assert u.read() == b'{"message": "hello world"}'


@responses.activate
def test_urlfile_iterable():
    responses.get(
        "https://example.com/some/url",
        body="one\ntwo\nthree\n",
        status=200,
    )

    u = URLFile("https://example.com/some/url")
    result = list(u)

    assert result == [b"one\n", b"two\n", b"three\n"]


@responses.activate
def test_urlfile_no_request_if_not_used():
    # This test would be failed by responses if the request were actually made,
    # as we've not registered the handler for it.
    URLFile("https://example.com/some/url")


@responses.activate
def test_urlfile_can_be_pickled():
    u = URLFile("https://example.com/some/url")

    result = pickle.loads(pickle.dumps(u))

    assert isinstance(result, URLFile)


@responses.activate
def test_urlfile_can_be_pickled_even_once_loaded():
    mock = responses.get(
        "https://example.com/some/url",
        json={"message": "hello world"},
        status=200,
    )

    u = URLFile("https://example.com/some/url", filename="my_file.txt")
    assert u.name == "my_file.txt"
    assert u.read() == b'{"message": "hello world"}'

    result = pickle.loads(pickle.dumps(u))

    assert isinstance(result, URLFile)
    assert result.name == "my_file.txt"
    assert result.read() == b'{"message": "hello world"}'

    assert mock.call_count == 2


@pytest.mark.parametrize(
    "url,filename",
    [
        # Simple URLs
        ("https://example.com/test", "test"),
        ("https://example.com/test.jpg", "test.jpg"),
        (
            "https://example.com/ហ_ត_អ_វ_ប_នជ_ក_រស_គតរបស_ព_រ_យ_ស_ម_នអ_ណ_ចម_ល_Why_Was_The_Death_Of_Jesus_So_Powerful_.m4a",
            "ហ_ត_អ_វ_ប_នជ_ក_រស_គតរបស_ព_រ_យ_ស_ម_នអ_ណ_ចម_ល_Why_Was_The_Death_Of_Jesus_So_Powerful_.m4a",
        ),
        # Data URIs
        (
            "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAUAAAAFCAYAAACNbyblAAAAHElEQVQI12P4//8/w38GIAXDIBKE0DHxgljNBAAO9TXL0Y4OHwAAAABJRU5ErkJggg==",
            "file.png",
        ),
        (
            "data:text/plain,hello world",
            "file.txt",
        ),
        (
            "data:application/data;base64,aGVsbG8gd29ybGQ=",
            "file",
        ),
        # URL-encoded filenames
        (
            "https://example.com/thing+with+spaces.m4a",
            "thing with spaces.m4a",
        ),
        (
            "https://example.com/thing%20with%20spaces.m4a",
            "thing with spaces.m4a",
        ),
        (
            "https://example.com/%E1%9E%A0_%E1%9E%8F_%E1%9E%A2_%E1%9E%9C_%E1%9E%94_%E1%9E%93%E1%9E%87_%E1%9E%80_%E1%9E%9A%E1%9E%9F_%E1%9E%82%E1%9E%8F%E1%9E%9A%E1%9E%94%E1%9E%9F_%E1%9E%96_%E1%9E%9A_%E1%9E%99_%E1%9E%9F_%E1%9E%98_%E1%9E%93%E1%9E%A2_%E1%9E%8E_%E1%9E%85%E1%9E%98_%E1%9E%9B_Why_Was_The_Death_Of_Jesus_So_Powerful_.m4a",
            "ហ_ត_អ_វ_ប_នជ_ក_រស_គតរបស_ព_រ_យ_ស_ម_នអ_ណ_ចម_ល_Why_Was_The_Death_Of_Jesus_So_Powerful_.m4a",
        ),
        # Illegal characters
        ("https://example.com/nulbytes\u0000.wav", "nulbytes_.wav"),
        ("https://example.com/nulbytes%00.wav", "nulbytes_.wav"),
        ("https://example.com/path%2Ftraversal.dat", "path_traversal.dat"),
        # Long filenames
        (
            "https://example.com/some/path/Biden_Trump_sows_chaos_makes_things_worse_U_S_hits_more_than_six_million_COVID_cases_WAPO_Trump_health_advisor_is_pushing_herd_immunity_strategy_despite_warnings_from_Fauci_medical_officials_Biden_says_he_hopes_to_be_able_to_visit_Wisconsin_as_governor_tells_Trump_to_stay_home_.mp3",
            "Biden_Trump_sows_chaos_makes_things_worse_U_S_hits_more_than_six_million_COVID_cases_WAPO_Trump_health_advisor_is_pushing_herd_immunity_strategy_despite_warnings_from_Fauci_medical_officials_Bide~.mp3",
        ),
        (
            "https://coppermerchants.example/complaints/𒀀𒈾𒂍𒀀𒈾𒍢𒅕𒆠𒉈𒈠𒌝𒈠𒈾𒀭𒉌𒈠𒀀𒉡𒌑𒈠𒋫𒀠𒇷𒆪𒆠𒀀𒄠𒋫𒀝𒁉𒄠𒌝𒈠𒀜𒋫𒀀𒈠𒄖𒁀𒊑𒁕𒄠𒆪𒁴𒀀𒈾𒄀𒅖𒀭𒂗𒍪𒀀𒈾𒀜𒁲𒅔𒋫𒀠𒇷𒅅𒈠𒋫𒀝𒁉𒀀𒄠.tablet",
            "𒀀𒈾𒂍𒀀𒈾𒍢𒅕𒆠𒉈𒈠𒌝𒈠𒈾𒀭𒉌𒈠𒀀𒉡𒌑𒈠𒋫𒀠𒇷𒆪𒆠𒀀𒄠𒋫𒀝𒁉𒄠𒌝𒈠𒀜𒋫𒀀𒈠𒄖𒁀𒊑𒁕𒄠𒆪𒁴𒀀𒈾𒄀𒅖~.tablet",
        ),
    ],
)
def test_get_filename(url, filename):
    assert get_filename(url) == filename


def test_secret_type():
    secret_value = "sw0rdf1$h"  # noqa: S105
    secret = Secret(secret_value)

    assert secret.get_secret_value() == secret_value
    assert str(secret) == "**********"


def test_truncate_filename_if_long():
    # Test that a file too long exception is not raised.
    random_str = "".join(
        random.SystemRandom().choice(string.ascii_uppercase + string.digits)
        for _ in range(350)
    )
    big_query = "query=" + random_str
    filename = "waffwyyg~.zip"
    url = "https://www.amazon.com/" + filename + "?" + big_query
    fileobj = io.BytesIO()
    url_path = URLPath(
        source=url,
        filename=filename + "?" + big_query,
        fileobj=fileobj,
    )
    assert url_path.filename == "waffwyyg~~.zip"
    _ = url_path.convert()
