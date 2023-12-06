"""
This file does what boto3 doesn't do: provides the mechanisms to sync a directory from s3.

The get_path method should require only ListObjects and GetObject
"""
import os
import boto3

from pathlib import Path


class XdbS3Sync(object):
    """
    Tool for retrieving and writing to AWS s3
    Recklessly copied from here: https://www.learnaws.org/2022/07/02/boto3-download-files-s3/

    In the wild, this requires GetObject and ListBucket permissions
    """
    def __init__(self, bucket_name):
        self.s3_client = boto3.client('s3')
        self.bucket_name = bucket_name

    def _get_files_folders(self, prefix):
        file_names = []
        folders = []

        default_kwargs = {
            "Bucket": self.bucket_name,
            "Prefix": prefix
        }
        next_token = ""

        while next_token is not None:
            updated_kwargs = default_kwargs.copy()
            if next_token != "":
                updated_kwargs["ContinuationToken"] = next_token

            response = self.s3_client.list_objects_v2(**updated_kwargs)
            contents = response.get("Contents", [])

            for result in contents:
                key = result.get("Key")
                if key[-1] == "/":
                    folders.append(key)
                else:
                    file_names.append(key)

            next_token = response.get("NextContinuationToken")

        return file_names, folders

    def _download_files(self, local_path, file_names, folders):
        local_path = Path(local_path)

        for folder in folders:
            folder_path = Path.joinpath(local_path, folder)
            # Create all folders in the path
            folder_path.mkdir(parents=True, exist_ok=True)

        for file_name in file_names:
            file_path = Path.joinpath(local_path, file_name)

            # Create folder for parent directory
            file_path.parent.mkdir(parents=True, exist_ok=True)
            self.s3_client.download_file(
                self.bucket_name,
                file_name,
                str(file_path)
            )

    def retrieve_s3_folder(self, s3_path, local_path):
        """
        the "prefix" here is the bracketed part of s3://<bucket_name>/<path/to/whatever>
        the "local path" is the path-to-BUCKET
        :param s3_path:
        :param local_path:
        :return:
        """
        if os.path.exists(local_path):
            if not os.path.isdir(local_path):
                raise FileExistsError(local_path)
        else:
            raise FileNotFoundError(local_path)

        files, folders = self._get_files_folders(s3_path)
        self._download_files(local_path, files, folders)
