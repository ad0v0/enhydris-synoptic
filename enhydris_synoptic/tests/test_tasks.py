import datetime as dt
import os
import shutil
import tempfile
import textwrap

from django.conf import settings
from django.http import HttpResponse
from django.test import TestCase, override_settings

import numpy as np
from enhydris.tests import RandomEnhydrisTimeseriesDataDir

from enhydris_synoptic.tasks import create_static_files

from .data import TestData


class RandomSynopticRoot(override_settings):
    """
    Override ENHYDRIS_SYNOPTIC_ROOT to a temporary directory.

    Specifying "@RandomSynopticRoot()" as a decorator is the same as
    "@override_settings(ENHYDRIS_SYNOPTIC_ROOT=tempfile.mkdtemp())", except
    that in the end it removes the temporary directory.
    """

    def __init__(self):
        self.tmpdir = tempfile.mkdtemp()
        super(RandomSynopticRoot, self).__init__(ENHYDRIS_SYNOPTIC_ROOT=self.tmpdir)

    def disable(self):
        super(RandomSynopticRoot, self).disable()
        shutil.rmtree(self.tmpdir)


def days_since_epoch(y, mo, d, h, mi):
    adelta = dt.datetime(y, mo, d, h, mi) - dt.datetime(1, 1, 1)
    return adelta.days + 1 + adelta.seconds / 86400.0


@RandomEnhydrisTimeseriesDataDir()
@RandomSynopticRoot()
class SynopticTestCase(TestCase):
    def assertHtmlContains(self, filename, text):
        """Check if a file contains an HTML extract.

        This is pretty much the same as self.assertContains() with html=True,
        but uses a filename instead of a response.
        """
        # We implement it by converting to an HTTPResponse, because there is
        # no better way to use self.assertContains() to do the actual job.
        with open(filename) as f:
            response = HttpResponse(f.read())
        self.assertContains(response, text, html=True)

    def setUp(self):
        self.data = TestData()
        settings.TEST_MATPLOTLIB = True
        create_static_files()

    def tearDown(self):
        settings.TEST_MATPLOTLIB = False

    def test_synoptic_group(self):
        filename = os.path.join(
            settings.ENHYDRIS_SYNOPTIC_ROOT, self.data.sg1.slug, "index.html"
        )
        self.assertHtmlContains(
            filename,
            text=textwrap.dedent(
                """\
            <div class="panel panel-default">
              <div class="panel-heading">
                <a href="station/{}/">Komboti</a>
              </div>
              <div class="panel-body">
                <dl class="dl-horizontal">
                  <dt>Last update</dt><dd>2015-10-22 15:20 EET (+0200)</dd>
                  <dt>&nbsp;</dt><dd></dd>
                  <dt>Rain</dt><dd>0 mm</dd>
                  <dt>Air temperature</dt><dd>17 °C</dd>
                  <dt>Wind (speed)</dt><dd>3.0 m/s</dd>
                  <dt>Wind (gust)</dt><dd>4.1 m/s</dd>
                </dl>
              </div>
            </div>
            """.format(
                    self.data.sgs_komboti.id
                )
            ),
        )
        self.assertHtmlContains(
            filename,
            text=textwrap.dedent(
                """\
            <div class="panel panel-default">
              <div class="panel-heading">
                <a href="station/{}/">Agios Athanasios</a>
              </div>
              <div class="panel-body">
                <dl class="dl-horizontal">
                  <dt>Last update</dt><dd>2015-10-23 15:20 EET (+0200)</dd>
                  <dt>&nbsp;</dt><dd></dd>
                  <dt>Rain</dt><dd>0.2 mm</dd>
                  <dt>Air temperature</dt><dd>38.5 °C</dd>
                </dl>
              </div>
            </div>
            """.format(
                    self.data.sgs_agios.id
                )
            ),
        )

    def test_synoptic_station(self):
        filename = os.path.join(
            settings.ENHYDRIS_SYNOPTIC_ROOT,
            self.data.sg1.slug,
            "station",
            str(self.data.sgs_agios.id),
            "index.html",
        )
        self.assertHtmlContains(
            filename,
            text=textwrap.dedent(
                """\
            <div class="panel panel-default">
              <div class="panel-heading">Latest measurements</div>
              <div class="panel-body">
                <dl class="dl-horizontal">
                  <dt>Last update</dt><dd>2015-10-23 15:20 EET (+0200)</dd>
                  <dt>&nbsp;</dt><dd></dd>
                  <dt>Rain</dt><dd>0.2 mm</dd>
                  <dt>Air temperature</dt><dd>38.5 °C</dd>
                </dl>
              </div>
            </div>
            """
            ),
        )

    def test_chart(self):
        # We will not compare a bitmap because it is unreliable; instead, we
        # will verify that an image was created and that the data that was used
        # in the image creation was correct. See
        # http://stackoverflow.com/questions/27948126#27948646

        # Check that it is a png of substantial length
        filename = os.path.join(
            settings.ENHYDRIS_SYNOPTIC_ROOT, "chart", str(self.data.sts2_2.id) + ".png"
        )
        self.assertTrue(filename.endswith(".png"))
        self.assertGreater(os.stat(filename).st_size, 100)

        # Retrieve data
        datastr = open(filename.replace("png", "dat")).read()
        self.assertTrue(datastr.startswith("(array("))
        datastr = datastr.replace("array", "np.array")
        data_array = eval(datastr)

        # Check that the data is correct
        desired_result = np.array(
            [
                [days_since_epoch(2015, 10, 23, 15, 00), 40],
                [days_since_epoch(2015, 10, 23, 15, 10), 39],
                [days_since_epoch(2015, 10, 23, 15, 20), 38.5],
            ]
        )
        np.testing.assert_allclose(data_array, desired_result)

    def test_grouped_chart(self):
        # Here we test the wind speed chart, which is grouped with wind gust.
        # See the comment in test_chart() above; the same applies here.

        # Check that it is a png of substantial length
        filename = os.path.join(
            settings.ENHYDRIS_SYNOPTIC_ROOT, "chart", str(self.data.sts1_3.id) + ".png"
        )
        self.assertTrue(filename.endswith(".png"))
        self.assertGreater(os.stat(filename).st_size, 100)

        # Retrieve data
        datastr = open(filename.replace("png", "dat")).read()
        self.assertTrue(datastr.startswith("(array("))
        datastr = datastr.replace("array", "np.array")
        data_array = eval(datastr)

        desired_result = (
            np.array(
                [
                    [days_since_epoch(2015, 10, 22, 15, 00), 3.7],
                    [days_since_epoch(2015, 10, 22, 15, 10), 4.5],
                    [days_since_epoch(2015, 10, 22, 15, 20), 4.1],
                ]
            ),
            np.array(
                [
                    [days_since_epoch(2015, 10, 22, 15, 00), 2.9],
                    [days_since_epoch(2015, 10, 22, 15, 10), 3.2],
                    [days_since_epoch(2015, 10, 22, 15, 20), 3],
                ]
            ),
        )
        np.testing.assert_allclose(data_array[0], desired_result[0])
        np.testing.assert_allclose(data_array[1], desired_result[1])
