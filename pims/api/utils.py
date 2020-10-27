from connexion.exceptions import UnsupportedMediaTypeProblem

PNG_MIMETYPES = {
    "image/png": "PNG",
}

WEBP_MIMETYPES = {
    "image/webp": "WEBP"
}

JPEG_MIMETYPES = {
    "image/jpg": "JPEG",
    "image/jpeg": "JPEG"
}

SUPPORTED_MIMETYPES = dict()
SUPPORTED_MIMETYPES.update(PNG_MIMETYPES)
SUPPORTED_MIMETYPES.update(JPEG_MIMETYPES)
SUPPORTED_MIMETYPES.update(WEBP_MIMETYPES)


def mimetype_to_mpl_slug(mimetype):
    """
    Return the format slug identifier used by Matplotlib for the given mime type.

    Matplotlib format slugs are: png, jpg, jpeg, ...
    See https://matplotlib.org/3.1.1/api/_as_gen/matplotlib.pyplot.savefig.html
    """
    if mimetype not in SUPPORTED_MIMETYPES.keys():
        raise UnsupportedMediaTypeProblem()

    return SUPPORTED_MIMETYPES[mimetype].lower()
