
def test_file(client, fake_files):
    for ff in fake_files.values():
        response = client.get("/file/{}/info/file".format(ff['filepath']))
        assert response.status_code == 200

        json = response.get_json()
        assert json["size"] == 0
        assert json["stem"] == ff['filepath'].split("/")[-1].split(".")[0]
        assert json["role"] in [ff['role'].upper().replace("VISUALISATION", "SPATIAL"), "NONE"]
        assert json["file_type"] == ("COLLECTION" if ff['collection'] else "SINGLE")
        assert json["is_symbolic"] == (ff['filetype'] == 'l')


def test_file_not_exists(client):
    response = client.get("/file/abc/info/file")
    assert response.status_code == 404


def test_image(client, fake_files):
    for ff in fake_files.values():
        response = client.get("/file/{}/info/image".format(ff['filepath']))
        assert response.status_code == (200 if not ff['collection'] else 404)
