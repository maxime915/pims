from connexion import ProblemException

from pims.api.utils import path2filepath


class FilepathNotFoundProblem(ProblemException):
    def __init__(self, filepath):
        filepath = path2filepath(filepath) if type(filepath) is not str else filepath
        title = 'Filepath not found'
        detail = 'The filepath {} does not exist.'.format(filepath)
        super(FilepathNotFoundProblem, self).__init__(status=404, title=title, detail=detail)


class NoAppropriateRepresentationProblem(ProblemException):
    def __init__(self, filepath, representation=None):
        filepath = path2filepath(filepath) if type(filepath) is not str else filepath
        title = 'No appropriate representation found'
        detail = 'The filepath {} does not have an appropriate representation'.format(filepath)
        if representation:
            detail += ' (expected {})'.format(representation)
        super(NoAppropriateRepresentationProblem, self).__init__(status=400, title=title, detail=detail)


class NoMatchingFormatProblem(ProblemException):
    def __init__(self, filepath):
        filepath = path2filepath(filepath) if type(filepath) is not str else filepath
        title = "No matching format found"
        detail = "The filepath {} is recognized by any of the available formats.".format(filepath)
        super(NoMatchingFormatProblem, self).__init__(status=400, title=title, detail=detail)


class FormatNotFoundProblem(ProblemException):
    def __init__(self, format_id):
        title = 'Format not found'
        detail = 'The format {} does not exist.'.format(format_id)
        super(FormatNotFoundProblem, self).__init__(status=404, title=title, detail=detail)


class ColormapNotFoundProblem(ProblemException):
    def __init__(self, colormap_id):
        title = 'Colormap not found'
        detail = 'The colormap {} does not exist.'.format(colormap_id)
        super(ColormapNotFoundProblem, self).__init__(status=404, title=title, detail=detail)
