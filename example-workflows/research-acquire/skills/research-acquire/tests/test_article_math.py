"""Article math stays singular without swallowing the prose after it."""

import unittest

from super_research import transport
from super_research.adapters import open_page


def article_record(body):
    url = "https://publisher.example/article"
    response = transport.TransportResponse(
        route_id=transport.WEB_PAGE_OPEN_ROUTE, url=url, status=200,
        body=body, content_type="text/html", observed_at="2026-09-12T12:00:00Z",
        channel_verdict=transport.ORIGIN_CONTENT,
    )
    return open_page.document_record(response, url)[0]


class ArticleMathTests(unittest.TestCase):
    def test_arxiv_alttext_keeps_percentage_and_exponent_once(self):
        # Math fragments from the saved arXiv paper's abstract and hardware section.
        record = article_record(r'''<article><h1>Nonlinear dynamics</h1>
        <p>Reynolds numbers of order <math id="abstract1.m1" class="ltx_Math"
        alttext="10^{2}" display="inline" intent=":literal"><semantics><msup><mn>10</mn><mn>2</mn></msup><annotation encoding="application/x-tex">10^{2}</annotation></semantics></math>.</p>
        <p>Gate fidelities achieved (above <math id="Sx5.SS4.p2.m1" class="ltx_Math"
        alttext="99" display="inline" intent=":literal"><semantics><mn>99</mn><annotation encoding="application/x-tex">99</annotation></semantics></math>%).</p>
        <p>Following paragraphs remain available.</p></article>''')
        self.assertEqual(record.body, "Nonlinear dynamics\nReynolds numbers of order 10^{2}.\n"
                         "Gate fidelities achieved (above 99%).\nFollowing paragraphs remain available.")
        self.assertEqual(record.author, "")
        self.assertEqual(record.published_at, "")

    def test_math_without_alttext_omits_alternative_annotations(self):
        for alttext in ("", ' alttext=" "'):
            with self.subTest(alttext=alttext):
                record = article_record('''<article><p>The equation is <math%s><semantics>
                <mrow><mi>x</mi><mo>=</mo><mn>1</mn></mrow>
                <annotation encoding="application/x-tex">x=1</annotation>
                <annotation-xml encoding="application/xhtml+xml"><p>Another rendering.</p>
                <meta name="author" content="Not the author"><time datetime="2020-01-01">An example date</time>
                <script type="application/ld+json">{"author":"Also not the author","datePublished":"2021-01-01"}</script>
                </annotation-xml></semantics></math> for this case.</p>
                <p>Next paragraph.</p></article>''' % alttext)
                self.assertEqual(record.body, "The equation is x=1 for this case.\nNext paragraph.")
                self.assertEqual(record.author, "")
                self.assertEqual(record.published_at, "")

    def test_alttext_skips_whole_subtree_and_preserves_page_metadata(self):
        record = article_record('''<html><head><title>A paper</title>
        <script type="application/ld+json">{"author":"Publisher author","datePublished":"2026-09-11"}</script>
        </head><body><article><p>Result: <math alttext="x &lt; 2"><semantics>
        <mrow><mi>x</mi><mo>&lt;</mo><mn>2</mn></mrow>
        <annotation-xml><p>Duplicate prose.</p><math alttext="nested">nested</math>
        <time datetime="2020-01-01">Unrelated date</time>
        <script type="application/ld+json">{"author":"Wrong author"}</script></annotation-xml>
        </semantics></math>.</p><nav><p>Navigation with <math alttext="bad">bad</math>.</p></nav>
        <p>Still here.<script>ignore()</script><style>.hidden {}</style></p>
        </article></body></html>''')
        self.assertEqual(record.body, "Result: x < 2.\nStill here.")
        self.assertEqual(record.title, "A paper")
        self.assertEqual(record.author, "Publisher author")
        self.assertEqual(record.published_at, "2026-09-11T00:00:00Z")

    def test_self_closing_math_does_not_hide_following_prose(self):
        record = article_record('''<article><p>A <math alttext="99"/>% result.
        <math alttext="10^{2}"><mspace/><annotation encoding="application/x-tex"/></math> trials.</p>
        <p>Next paragraph.</p></article>''')
        self.assertEqual(record.body, "A 99% result. 10^{2} trials.\nNext paragraph.")


if __name__ == "__main__":
    unittest.main()
