"""what is a blog?

A blog has date sensitive entries

one page per entry with a previous and next links

and one or more index pages with with older and newer links which
lists the headline and a teaser for each blog entry

"""
from pyramid import view, config
from pyramid.static import static_view
import jinja2
from webob import Response
from filesys import FileContainer, FileResource, FileSystemRootFactory, FileSystemBase, Templateable
from bs4 import BeautifulSoup as bs
from markdown import Markdown
import os
import logging
import cStringIO
import time
log = logging.getLogger(__name__)

md_extensions = ["meta", "codehilite"]


class BlogPage(Templateable, FileSystemBase):
    """represents a blog entry generated from markdown(assumed)

    it passes the blogentry as context
    dict(title,published_date,body,author,teaser)

    the template the context gets handed to is configurable.

    first the blogentry.template attribute is consulted

    then blog_entry_template in the application settings if
    blogentry.template is None

    if all else fails then blog_entry.html in the current directory is
    used(if found)

    """
    def __init__(self, request, path, parent=None):
        assert parent, "Parent is required"
        assert isinstance(parent, BlogEntry), "parent must be a BlogEntry"
        super(BlogPage, self).__init__(request, path, parent=parent.__parent__)
        self.entry = parent

    def get_template(self):
        try:
            override_template = self.entry.__parent__["blog_entry.html"].url
        except KeyError:
            override_template = None

        the_template = self.entry.template or \
                       override_template or \
                       self.request.registry.settings.get("blog_entry_template",
                                                          None)
        return self.request.registry["env"].get_template(the_template)

    def get_template_context(self):
        return dict(title=self.entry.title,
                    published_date=self.entry.published_date,
                    body=self.entry.body,
                    author=self.entry.author,
                    teaser=self.entry.teaser)


class BlogEntry(FileResource):
    """parses a markdown file (*.md) looks for meta data for the blog
    entry such as title, published_date, body, author, tempate and
    teaser


    it then creates a BlogPage for the html generation

    """
    title = None
    published_date = None
    body = None
    author = None
    template = None
    teaser = None
    EXT = [".md", ]
    content_type = "text/plain"

    def __init__(self, request, path, parent=None):
        super(BlogEntry, self).__init__(request, path, parent=parent)
        self.base_name, self.ext = os.path.splitext(path)
        assert self.ext.lower() in self.EXT, " %s is not a markdown file" % path
        m = Markdown(extensions=md_extensions)
        m.Meta = {}
        body = cStringIO.StringIO()
        m.convertFile(input=open(self.path), output=body)
        self.body = body.getvalue()
        body.close()

        for k, v in m.Meta.items():
            setattr(self, k, " ".join(v))

        setattr(self, "published_date", time.ctime(getattr(self, "published_date")) or time.ctime(os.path.getctime(path)))
        setattr(self, "template", getattr(self, "template") or request.registry.settings["blog_entry_template"])
        self.page = BlogPage(request, "%s.html" % self.base_name, self)


class BlogIndex(FileResource):
    """marker object used by traversal to route to a view that generates
    the index of blog entries
    """
    pass


class BlogContainer(FileContainer):
    """a container used for traversal and handles blog entries authored in
    Markdown

    during traversal if index.html is recieved as a key returns a
    BlogIndex object which causes the view_index view to run

    """
    RESOURCE = BlogEntry

    def __init__(self, request, path, parent=None):
        super(BlogContainer, self).__init__(request, path, parent=parent)
        self._file_container = FileContainer(request, path, parent=parent)
        self._generated_files = {}

    def __getitem__(self, key):
        """
        could return a

        blog index file or
        blog entry or
        blog page
        a file
        """
        #special case, if this is the root and key==index.html, return BlogIndex
        if key == "index.html" and (not self.__parent__ or not isinstance(self.__parent__, BlogContainer)):
            return BlogIndex(self.request, "%s/index.html" % self.path, self)

        try:
            # assume parsed as blogentry

            entry = super(BlogContainer, self).__getitem__(key)
            if isinstance(entry, BlogEntry):
                self._generated_files[entry.page.__name__] = entry.page # for __iter__
            return entry
        except Exception as ex:
            if isinstance(ex, KeyError):
                base_name, ext = os.path.splitext(key)
                if ext and ext.lower() == ".html":
                    log.warn("internal redirect to generated page for %s" % key)
                    entry = super(BlogContainer, self).__getitem__("%s.md" % base_name).page
                    if entry.__name__ == key:
                        return entry
                    else:
                        raise
                else:
                    raise
            else:
                #try as file
                log.warn("uhoh", exc_info=True)
                return self._file_container[key]

    def __iter__(self):
        for item in super(BlogContainer, self).__iter__():
            yield item
        for item in self._generated_files.values():
            yield item


@view.view_config(context=BlogIndex)
def view_index(context, request):
    """
    list of blog entries as context for the template (sorted by published_date or file created_by)
    template_context = dict(context=context, request=request, entries=entries)
    """
    print [e.path for e in context.__parent__]
    entries = (e for e in context.__parent__ if isinstance(e, BlogEntry))
    sorted_entries = sorted(entries, key=lambda x: x.published_date, reverse=True)
    content = context.render_as_template(entries=sorted_entries)
    return Response(body=content)


class BlogRootFactory(FileSystemRootFactory):
    CONTAINER = BlogContainer
