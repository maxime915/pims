from datetime import datetime

from pims.files.file import Path


def test_basic_file(app):
    with app.app_context():
        path = Path(app.config['FILE_ROOT_PATH'], "upload0/myfile.svs")
        assert path.exists()
        assert path.size == 0
        assert (datetime.today() - path.creation_datetime).days == 0


def test_extensions(app):
    with app.app_context():
        files = ("upload0/myfile.svs", "upload2/processed/myfile.ome.tiff", "upload5/processed/visualisation.mrxs.format")
        extensions = (".svs", ".ome.tiff", ".mrxs.format")

        for f, ext in zip(files, extensions):
            path = Path(app.config['FILE_ROOT_PATH'], f)
            assert path.extension == ext
            assert path.true_stem == f.split("/")[-1].replace(ext, "")


def test_upload_root(app, fake_files):
    with app.app_context():
        root = Path(app.config['FILE_ROOT_PATH'])
        fake_names = fake_files.keys()
        for ff in fake_names:
            path = root / Path(ff)
            assert path.upload_root() == root / Path(ff.split("/")[0])


def test_roles(app, fake_files):
    with app.app_context():
        root = Path(app.config['FILE_ROOT_PATH'])
        for ff in fake_files.values():
            name = ff['filepath']
            role = ff['role']
            path = root / Path(name)
            if role == "upload":
                assert path.has_upload_role()
                assert not path.has_original_role()
                assert not path.has_spatial_role()
                assert not path.has_spectral_role()
            elif role == "original":
                assert not path.has_upload_role()
                assert path.has_original_role()
                assert not path.has_spatial_role()
                assert not path.has_spectral_role()
            elif role == "visualisation":
                assert not path.has_upload_role()
                assert not path.has_original_role()
                assert path.has_spatial_role()
                assert not path.has_spectral_role()
            elif role == "spectral":
                assert not path.has_upload_role()
                assert not path.has_original_role()
                assert not path.has_spatial_role()
                assert path.has_spectral_role()
            else:
                assert not path.has_upload_role()
                assert not path.has_original_role()
                assert not path.has_spatial_role()
                assert not path.has_spectral_role()


def test_collection(app, fake_files):
    with app.app_context():
        root = Path(app.config['FILE_ROOT_PATH'])
        for ff in fake_files.values():
            name = ff['filepath']
            is_collection = ff['collection']
            path = root / Path(name)
            assert path.is_collection() == is_collection
            assert path.is_single() == (not is_collection)
