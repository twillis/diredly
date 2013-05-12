import os
from pyramid import view, traversal
from webob import Response
from pyramid import config
from pyramid.static import static_view
import jinja2
import logging
import mimetypes
logging.basicConfig(level=logging.WARN)
log = logging.getLogger(__name__)


class FileSystemBase(object):
    """common initializing functionality shared between files and
    directories
    """
    def __init__(self, request, path, parent=None):
        self.request = request
        self.path = os.path.abspath(path)
        self.__name__ = os.path.split(self.path)[1]
        self.__parent__ = parent

    @property
    def url(self):
        return traversal.resource_path(self)

    @property
    def root_url(self):
        return self.request.root.url


class Templateable(object):
    """establishes the protocol for generating content based on context
    and a template
    """
    request = None
    path = None
    __name__ = None

    def get_template(self):
        """
        by default the path is the template but there could be
        specializations that select a different template
        """
        return self.request.registry["env"].get_template(traversal.resource_path(self))

    def get_template_context(self):
        """
        by default provide self as context and the attached request, but
        there could be specializations to this
        """
        return dict(context=self, request=self.request)

    def render_as_template(self, **template_context):
        template_context.update(**self.get_template_context())
        try:
            the_template = self.get_template()
            return the_template.render(template_context)
        except Exception as ex:
            log.warn("could not render %s as template" % self.path, exc_info=True)
            return None

    @property
    def content_type(self):
        t, _ = mimetypes.guess_type(self.__name__)
        if t:
            return t
        else:
            log.warning("could not determine content_type of %s falling back to text/html" % self.__name__)
            return "text/html"


class FileResource(Templateable, FileSystemBase):
    """
    encapsulates a file resource
    """

    def __init__(self, request, path, parent=None):
        super(FileResource, self).__init__(request, path, parent=parent)
        assert os.path.isfile(self.path), "not a file"


class FileContainer(FileSystemBase):
    """
    encapsulates a directory resource
    """
    RESOURCE = FileResource

    def __init__(self, request, path, parent=None):
        super(FileContainer, self).__init__(request, path, parent=parent)
        assert not os.path.isfile(self.path), "not a container"

    def __getitem__(self, key):
        """used by pyramid for traversal each segment of the path is passed
        in until a KeyError is raised the last object returned is then
        used as the context for view consideration
        key is interpreted to be either a path to a file or sub-directory
        """
        if key.endswith("~") or key.startswith("."):
            raise KeyError(key)

        path = os.path.join(self.path, key)
        handlers = self.request.registry["handlers"]
        if traversal.resource_path(self, key) in handlers:
            handle = handlers[traversal.resource_path(self, key)]
        else:
            handle = self.__class__

        if os.path.isfile(path):
            return self.RESOURCE(self.request, path, parent=self)
        elif os.path.isdir(path):
            return handle(self.request, path, parent=self)
        else:
            raise KeyError(path)

    def __iter__(self):
        """
        support {item for item in self}
        """
        for item in os.listdir(self.path):
            try:
                item_resource = self[item]
                yield item_resource
            except KeyError:
                continue
            if isinstance(item_resource, FileContainer):
                for child_item_resource in item_resource:
                    yield child_item_resource


class FileSystemRootFactory(object):
    """
    initializes a FileContainer(directory) for the root path
    """
    CONTAINER = FileContainer

    def __init__(self, path):
        self.path = os.path.abspath(path)

    def __call__(self, request):
        """called when the application recieves a request whatever is
        returned is what pyramid will use to traverse and assign a
        context which is then used to figure out what view to select
        """
        result = self.CONTAINER(request, self.path)
        # keep root dir out of path names exposed
        result.__name__ = None
        return result


@view.view_config(context=Templateable)
def view_file(context, request):
    """return content of file as response body

    if file is a template, render with context(what is this?)
    somehow, a theme wrapper needs to be applied before it goes
    out. perhaps that cool middleware ian bicking wrote 10 years
    ago....tempita???

    put this in too
    http://docs.webob.org/en/latest/file-example.html
    """
    if context.content_type == "text/html":
        content = context.render_as_template()
    else:
        content = None

    if content:
        return Response(body=context.render_as_template(),
                        content_type=context.content_type)
    else:
        return request.registry["static"](context, request)


@view.view_config(context=FileContainer)
def view_index(context, request):
    """
    handles the /**/*/ redirect to /**/*/index.html
    """
    if context.__name__:
        location = "%s/index.html" % request.resource_url(context)
    else:
        location = "index.html"

    return Response(status=302,
                    headers=[("Location", location)])


@view.view_config(context=FileContainer, name="list")
def view_walk(context, request):
    """
    return a list of files delimited by \n as response body
    """
    return Response("\n".join([traversal.resource_path(child)
                               for child in context]),
                    content_type="text/plain")


def application(global_settings=None, content=".", **settings):
    loaders = []
    app_settings = global_settings or {}
    app_settings.update(settings)
    handlers = {k: v for k, v in settings.items() if k.startswith("/")}

    if not os.path.isdir(os.path.abspath(content)):
        raise ValueError("path: %s does not exist" % os.path.abspath(content))
    else:
        log.debug("setting content to %s" % os.path.abspath(content))
        loaders.append(jinja2.FileSystemLoader(os.path.abspath(content)))

    c = config.Configurator(root_factory=FileSystemRootFactory(path=content), settings=app_settings)
    c.scan()

    c.registry["env"] = jinja2.Environment(loader=jinja2.ChoiceLoader(loaders))
    c.registry["static"] = static_view(root_dir=os.path.abspath(content))
    c.registry["handlers"] = {}
    if handlers:
        for url, handler in handlers.items():
            _module, obj = handler.rsplit(".", 1)
            c.registry["handlers"][url] = getattr(__import__(_module, fromlist=obj), obj)
    return c.make_wsgi_app()
