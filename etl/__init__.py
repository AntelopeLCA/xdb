import os

from antelope_core import FileAccessor
from patoolib import repack_archive

from .solids.run_static_catalog import run_static_catalog

from antelope_manager.static.index_and_order import is_7z, IndexAndOrder


def de7zip(existing7z):
    """
    A 2.57 GiB xml database (ei3.7.1 cutoff) occupies 59 MiB in 7z and 226MiB in zip.  However, access times to the
    7z are very slow.

    This function uses patoolib.repack_archive to unpack an existing file from 7z and repack in standard zip.

    Requires ~10min for the above db (thinkpad i5-5300U @ 2.30GHz, prolly much faster on the cloud

    :param existing7z:
    :return:
    """
    if is_7z(existing7z):
        basename, ext = os.path.splitext(existing7z)
        newname = basename + '.zip'
        repack_archive(existing7z, newname)
        os.remove(existing7z)


CONFIG_ORIGINS = TEST_ORIGINS = ('ecoinvent.3.7.1.cutoff', )

CAT_ROOT = os.environ.get('ANTELOPE_CATALOG_ROOT')  # help??


def preprocess_resources(data_root, origins):
    aws = FileAccessor(data_root)
    assert set(aws.origins) == set(CONFIG_ORIGINS)

    for origin in origins:
        src = next(aws.gen_sources(origin, 'exchange'))
        aio = IndexAndOrder(aws, origin, src)
        aio.run()
