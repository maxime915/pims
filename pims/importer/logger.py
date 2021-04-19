from cytomine.models import UploadedFile


class ImportListener:
    def start_import(self, path, *args, **kwargs):
        pass

    def file_moved(self, old_path, new_path, *args, **kwargs):
        pass

    def file_not_found(self, path, *args, **kwargs):
        pass

    def file_not_moved(self, path, *args, **kwargs):
        pass

    def start_format_detection(self, path, *args, **kwargs):
        pass

    def no_matching_format(self, path, *args, **kwargs):
        pass

    def matching_format_found(self, path, format, *args, **kwargs):
        pass

    def created_role_file(self, path, role, *args, **kwargs):
        pass

    def generic_file_error(self, path, *args, **kwargs):
        pass

    def failed_integrity_check(self, path, *args, **kwargs):
        pass

    def passed_integrity_check(self, path, *args, **kwargs):
        pass

    def import_success(self, path, *args, **kwargs):
        pass


class CytomineListener(ImportListener):
    def __init__(self, root_id, uploaded_file_id):
        self.path_uf_mapping = dict()

        root = UploadedFile().fetch(root_id)
        self.path_uf_mapping[root.path] = root

        if uploaded_file_id != root_id:
            uf = UploadedFile().fetch(uploaded_file_id)
            self.path_uf_mapping[uf.path] = uf

    def propagate_error(self, uf):
        pass  # TODO: propagate error to parents

    def start_import(self, path, *args, **kwargs):
        uf = self.path_uf_mapping[path]
        uf.status = UploadedFile.EXTRACTING_DATA
        uf.update()

    def file_moved(self, old_path, new_path, *args, **kwargs):
        uf = self.path_uf_mapping[old_path]
        uf.path = new_path  # TODO
        uf.update()
        self.path_uf_mapping[new_path] = uf

    def file_not_moved(self, path, *args, **kwargs):
        uf = self.path_uf_mapping[path]
        uf.status = UploadedFile.ERROR_EXTRACTION
        uf.update()
        self.propagate_error(uf)

    def file_not_found(self, path, *args, **kwargs):
        uf = self.path_uf_mapping[path]
        uf.status = UploadedFile.ERROR_EXTRACTION
        uf.update()
        self.propagate_error(uf)

    def start_format_detection(self, path, *args, **kwargs):
        uf = self.path_uf_mapping[path]
        uf.status = UploadedFile.DETECTING_FORMAT
        uf.update()
        self.propagate_error(uf)

    def no_matching_format(self, path, *args, **kwargs):
        uf = self.path_uf_mapping[path]
        uf.status = UploadedFile.ERROR_FORMAT
        uf.update()
        self.propagate_error(uf)

    def matching_format_found(self, path, format, *args, **kwargs):
        uf = self.path_uf_mapping[path]
        uf.contentType = format.get_identifier()  # TODO: not the content type
        uf.update()

