"""
or.... can i figure out how to use traversal + jinja to make a
mechanism for generating static sites.
"""
import unittest
import pyramid as p
from webob import Request
import os
import uuid
from diredly.filesys import FileSystemRootFactory, FileResource, application
from diredly.blog import BlogContainer
from webob import Request

__here__ = os.path.abspath(os.path.dirname(__file__))

TEST_FILES = ("index.html",
              "menu.html",
              "directions.html",
              "hightea.html",
              "images/header.gif")


def make_request(path="/"):
    request = Request.blank(path)
    request.registry = dict(handlers={})
    return request


class TestDispatch(unittest.TestCase):
    def testCanIEnumeratePages(self):
        f = FileSystemRootFactory(os.path.join(__here__, "tstsite"))(make_request())

        #these are files that exist
        for r in ("index.html",
                  "menu.html",
                  "directions.html",
                  "hightea.html"):
            self.assert_(isinstance(f[r], FileResource), msg=(r, f[r]))
            self.assertEquals(f[r].__name__, r)

        # this file exists
        f["images"]["header.gif"]

        #this does not exist and should raise a keyerror
        with self.assertRaises(KeyError) as ctx:
            f[str(uuid.uuid4())]

    def testCanIGetAListOfPages(self):
        app = application(content=os.path.join(__here__, "tstsite"))
        res = Request.blank("list").send(app)
        self.assertEquals(res.status_int, 200)
        THE_FILES = res.body.split("\n")
        for f in TEST_FILES:
            # server will return with leading /
            self.assertIn("/%s" % f, THE_FILES)

    def testCanIRenderPages(self):
        app = application(content=os.path.join(__here__, "tstsite"))
        for r in TEST_FILES:
            res = Request.blank(r).send(app)
            print str(res)
            self.assertEquals(200, res.status_int)


class TestBlogPlugin(unittest.TestCase):

    def testcanIParseABlogEntry(self):
        class BlogRootFactory(FileSystemRootFactory):
            CONTAINER = BlogContainer

            def __call__(self, request):
                return super(BlogRootFactory, self).__call__(request)

        f = BlogRootFactory(__here__)(make_request())

        result = f["tstblogentry.md"]
        self.assert_(isinstance(result, BlogRootFactory.CONTAINER.RESOURCE))
        self.assert_("is a blog" in result.body)
        fallback_result = f["templates"]
        self.assert_(isinstance(fallback_result,
                                FileSystemRootFactory.CONTAINER))
        self.assert_(isinstance(fallback_result["index.html"],
                                FileSystemRootFactory.CONTAINER.RESOURCE))

    def testCanIGetAListOfBlogEntries(self):
        class BlogRootFactory(FileSystemRootFactory):
            CONTAINER = BlogContainer

            def __call__(self, request):
                return super(BlogRootFactory, self).__call__(request)

        f = BlogRootFactory(__here__)(make_request())
        l = [x.path for x in f]
        self.assert_(os.path.join(__here__, "tstblogentry.html") in l, (l, list(f)))

    def testCanICreateAPageableBlogIndex(self):
        pass
