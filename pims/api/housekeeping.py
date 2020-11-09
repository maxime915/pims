from pims.api.exceptions import check_path_existence, NotADirectoryProblem
from pims.api.utils import filepath2path


def _usage_as_dict(path):
    usage = path.mount_disk_usage()
    size = path.size
    mount_point = path.mount_point()
    return {
        "mount_point": str(mount_point) if mount_point else None,
        "mount_available_size": usage.free,
        "mount_total_size": usage.total,
        "mount_used_size": usage.used,
        "mount_used_size_percentage": float(usage.used) / float(usage.total) * 100,
        "used_size": size,
        "used_size_percentage": float(size) / float(usage.total) * 100
    }


def show_path_usage(directorypath):
    path = filepath2path(directorypath)
    check_path_existence(path)
    if not path.is_dir():
        raise NotADirectoryProblem(directorypath)

    return _usage_as_dict(path)


def show_disk_usage():
    return _usage_as_dict(filepath2path("."))


def show_disk_usage_v1():
    data = show_disk_usage()
    return {
        "available": data["mount_available_size"],
        "used": data["mount_used_size"],
        "usedP": data["mount_used_size_percentage"] / 100,
        "hostname": None,
        "ip": None,
        "mount": data["mount_point"]
    }
