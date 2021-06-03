from .file_accessor import AwsFileAccessor


class AwsResourceLoader(AwsFileAccessor):
    """
    This class crawls the synced AWS directory and adds all the specified resources to the catalog provided as
    an input argument.

    After loading all pre-initialized resources, the class runs check_bg on each origin to auto-generate a
    background ordering within the catalog's filespace if one does not already exist.
    """

    def _load_origin(self, cat, org):
        """
        First we add exchange resources- the
        :param org:
        :return:
        """
        for iface in ('exchange', 'index', 'background'):
            for i, source in enumerate(self.gen_sources(org, iface)):
                res = self.create_resource(source)
                cat.add_resource(res)
                res.check(cat)

    def load_resources(self, cat):
        for org in self.origins:
            self._load_origin(cat, org)
            cat.query(org).check_bg()
