#!/usr/bin/env python
import sys
import os
import contextlib
import threading
import tempfile
import shutil
import hashlib
import unittest
import urllib2
import zipfile
import cStringIO
import wsgiref.simple_server
import selenium.webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support.select import Select

import ahgl_admin


def get_web_driver():
  return selenium.webdriver.Chrome()

def get_sql_files():
  files = ['./schema.sql', './test_data.sql']
  if os.environ.get("TEST_SKIP_LINEUP"):
    files.append('./test_lineup.sql')
  return files

def get_test_replay_file():
  return './test_fake_replay.dat'

TEST_REPLAY_SHA1 = '4e1243bd22c66e76c2ba9eddc1f91394e57f9f83'

class AhglAdminSiteBrowserTest(unittest.TestCase):

  def setUp(self):
    self.wd = get_web_driver()
    self.data_dir = tempfile.mkdtemp()
    ahgl_admin.app.debug = True  # TODO: drop
    ahgl_admin.app.config['DATA_DIR'] = self.data_dir
    ahgl_admin.app.config['SEASON'] = '2'
    ahgl_admin.app.secret_key = 'AHGL'
    self.httpd = wsgiref.simple_server.make_server('', 0, ahgl_admin.app.wsgi_app)
    self.base_url = 'http://localhost:%d/' % self.httpd.server_address[1]
    threading.Thread(target=self.httpd.serve_forever).start()
    print self.data_dir  # TODO: drop

  def tearDown(self):
    if not os.environ.get("TEST_PRESERVE"):
      self.httpd.shutdown()
      self.wd.close()
      shutil.rmtree(self.data_dir)

  def runTest(self):
    db_conn = ahgl_admin.open_db(os.path.join(self.data_dir, 'ahgl.sq3'))
    for fname in get_sql_files():
      with open(fname) as handle:
        db_conn.executescript(handle.read())
    db_conn.commit()

    wd = self.wd
    bu = self.base_url
    css = wd.find_element_by_css_selector
    xpath = wd.find_element_by_xpath
    def wait_title(val):
      WebDriverWait(wd, 1).until(lambda w: w.title == val)
    block_xpath_fmt = '//h2[text()="%s"]/following-sibling::p[1]'
    subhead_xpath_fmt = '//h2[text()="%s"]/following-sibling::h3[%d]'

    wd.get(bu)
    self.assertEqual(css('h1').text, 'AHGL Admin Page')

    def login(team):
      with contextlib.closing(db_conn.cursor()) as cursor:
        cursor.execute(
            'SELECT auth_key FROM accounts WHERE team = '
            '(SELECT id FROM teams WHERE name =?) '
            , (team,))
        auth_key = list(cursor)[0][0]
      wd.get(bu + 'login/' + auth_key)

    def login_admin():
      with contextlib.closing(db_conn.cursor()) as cursor:
        cursor.execute(
            'SELECT auth_key FROM accounts WHERE team = -1')
        auth_key = list(cursor)[0][0]
      wd.get(bu + 'login/' + auth_key)

    wd.find_element_by_link_text('Enter Lineup').click()
    wait_title('No Account')
    wd.get(bu)
    wd.get(bu + 'login/foo')
    wait_title('No Account')
    login('Twitter')
    wait_title('AHGL Admin Page')
    wd.find_element_by_link_text('Enter Lineup').click()
    wait_title('AHGL Lineup Entry')
    wd.get(bu + 'logout')
    wait_title('AHGL Admin Page')
    wd.find_element_by_link_text('Enter Lineup').click()
    wait_title('No Account')
    wd.get(bu)

    def enter_maps(week, mapnames):
      login_admin()
      wd.find_element_by_link_text('Enter Maps').click()
      wait_title('AHGL Map Entry')

      self.assertEqual(css('h1').text, 'AHGL Map Entry')
      self.assertEqual(css('h2').text, 'Week %d' % week)
      for number, mapname in enumerate(mapnames):
        Select(css('select[name=map_%d]' % (number+1))).select_by_visible_text(mapname)

      css('input[type=submit]').submit()
      WebDriverWait(wd, 1).until(lambda w: w.title != 'AHGL Map Entry')

      self.assertEqual(wd.title, 'Success')
      wd.get(bu)


    def enter_lineup(week, team, players, ref):
      login(team)
      wd.find_element_by_link_text('Enter Lineup').click()
      wait_title('AHGL Lineup Entry')

      self.assertEqual(css('h1').text, 'AHGL Lineup Entry')
      self.assertEqual(css('h2').text, 'Week %d' % week)

      for (number, (name, race)) in enumerate(players):
        Select(css('select[name=player_%d]' % (number+1))).select_by_visible_text(name)
        Select(css('select[name=race_%d]' % (number+1))).select_by_visible_text(race)

      css('input[name=referee]').send_keys(ref)

      css('input[type=submit]').submit()
      WebDriverWait(wd, 1).until(lambda w: w.title != 'AHGL Lineup Entry')

      self.assertEqual(wd.title, 'Success')
      wd.get(bu)


    enter_maps(1, [
      "Xel'Naga Caverns",
      "Tal'Darim Altar",
      "Backwater Gulch",
      "Metalopolis",
      "Shattered Temple",
      ])


    if not os.environ.get("TEST_SKIP_LINEUP"):
      enter_lineup(1, 'Twitter', [
        ('implausible', 'P'),
        ('xelnaga', 'Z'),
        ('ceaser', 'P'),
        ('arya', 'P'),
        ],
        "TwitterRef")

      enter_lineup(1, 'Zynga', [
        ('ShamWOW', 'Z'),
        ('joolz', 'P'),
        ('Preposterous', 'Z'),
        ('Fredo', 'Z'),
        ],
        "ZyngaRef")

      enter_lineup(1, 'Facebook', [
        ('JohnOldman', 'Z'),
        ('tstanke', 'P'),
        ('bingobango', 'Z'),
        ('icecreamboy', 'Z'),
        ],
        "FacebookRef")

      enter_lineup(1, 'Amazon', [
        ('MuffinTopper', 'P'),
        ('Dasnor', 'Z'),
        ('SteelCurtain', 'T'),
        ('Skynet', 'Z'),
        ],
        "AmazonRef")

    login('Twitter')

    wd.find_element_by_link_text('Show Lineup').click()
    wait_title('AHGL Select Lineup Week')
    wd.find_element_by_link_text('Week 1').click()
    wait_title('AHGL Lineup')

    self.assertEqual(xpath(block_xpath_fmt % 'Match 1: Twitter vs Zynga').text,
        'implausible.931 (P) < Xel\'Naga Caverns > (Z) ShamWOW.657\n'
        'xelnaga.195 (Z) < Tal\'Darim Altar > (P) joolz.395\n'
        'ceaser.610 (P) < Backwater Gulch > (Z) Preposterous.925\n'
        'arya.COWARD (P) < Metalopolis > (Z) Fredo.746\n'
        'ACE (?) < Shattered Temple > (?) ACE'
        )
    self.assertEqual(xpath(block_xpath_fmt % 'Match 2: Facebook vs Dropbox').text,
        'LINEUP ENTERED <> NOT ENTERED')
    self.assertEqual(xpath(block_xpath_fmt % 'Match 3: Yelp vs Amazon').text,
        'NOT ENTERED <> LINEUP ENTERED')
    self.assertEqual(xpath(block_xpath_fmt % 'Match 4: Microsoft vs Google').text,
        'NOT ENTERED <> NOT ENTERED')

    self.assertEqual(xpath(subhead_xpath_fmt % ('Match 1: Twitter vs Zynga', 1)).text,
      'Suggested channel: ahgl-1')
    self.assertEqual(xpath(subhead_xpath_fmt % ('Match 2: Facebook vs Dropbox', 1)).text,
      'Suggested channel: ahgl-2')
    self.assertEqual(xpath(subhead_xpath_fmt % ('Match 3: Yelp vs Amazon', 1)).text,
      'Suggested channel: ahgl-3')
    self.assertEqual(xpath(subhead_xpath_fmt % ('Match 4: Microsoft vs Google', 1)).text,
      'Suggested channel: ahgl-4')

    self.assertEqual(xpath(subhead_xpath_fmt % ('Match 1: Twitter vs Zynga', 2)).text,
      'Captains: Captain Foo AND Captain Bar')
    self.assertEqual(xpath(subhead_xpath_fmt % ('Match 2: Facebook vs Dropbox', 2)).text,
      'Captains: Captain Baz AND Captain Drop')
    self.assertEqual(xpath(subhead_xpath_fmt % ('Match 3: Yelp vs Amazon', 2)).text,
      'Captains: Captain Local AND Captain Jeff')
    self.assertEqual(xpath(subhead_xpath_fmt % ('Match 4: Microsoft vs Google', 2)).text,
      'Captains: Captain Nato AND Captain Larry')

    self.assertEqual(xpath(subhead_xpath_fmt % ('Match 1: Twitter vs Zynga', 3)).text,
      'Referees: Facebook (FacebookRef) AND Dropbox (no ref)')
    self.assertEqual(xpath(subhead_xpath_fmt % ('Match 2: Facebook vs Dropbox', 3)).text,
      'Referees: Twitter (TwitterRef) AND Zynga (ZyngaRef)')
    self.assertEqual(xpath(subhead_xpath_fmt % ('Match 3: Yelp vs Amazon', 3)).text,
      'Referees: Microsoft (no ref) AND Google (no ref)')
    self.assertEqual(xpath(subhead_xpath_fmt % ('Match 4: Microsoft vs Google', 3)).text,
      'Referees: Yelp (no ref) AND Amazon (AmazonRef)')

    wd.get(bu)

    wd.find_element_by_link_text('Enter Result').click()
    wait_title('AHGL Result Entry')
    self.assertEqual(css('h1').text, 'AHGL Result Entry')

    Select(css('select[name=match]')).select_by_visible_text('Twitter (Home) vs Zynga (Away)')

    css('input[name=winner_1][value=home]').click()
    css('input[name=winner_2][value=away]').click()
    css('input[name=winner_3][value=away]').click()
    css('input[name=winner_4][value=away]').click()
    css('input[name=winner_5][value=none]').click()

    css('input[name=replay_1]').send_keys(os.path.abspath(get_test_replay_file()))

    css('input[type=submit]').submit()
    WebDriverWait(wd, 1).until(lambda w: w.title != 'AHGL Result Entry')

    self.assertEqual(wd.title, 'Success')
    wd.get(bu)

    wd.find_element_by_link_text('Show Result').click()
    wait_title('AHGL Select Result Week')
    wd.find_element_by_link_text('Week 1').click()
    wait_title('AHGL Result')

    self.assertEqual(xpath(block_xpath_fmt % 'Match 1: Twitter vs Zynga').text,
        'Game 1 (Xel\'Naga Caverns): implausible.931 (P) > (Z) ShamWOW.657 -- replay\n'
        'Game 2 (Tal\'Darim Altar): xelnaga.195 (Z) < (P) joolz.395 -- no replay\n'
        'Game 3 (Backwater Gulch): ceaser.610 (P) < (Z) Preposterous.925 -- no replay\n'
        'Game 4 (Metalopolis): arya.COWARD (P) < (Z) Fredo.746 -- no replay\n'
        'Game 5 (Shattered Temple): Not played'
        )
    self.assertEqual(xpath(block_xpath_fmt % 'Match 2: Facebook vs Dropbox').text,
        'No result entered')
    self.assertEqual(xpath(block_xpath_fmt % 'Match 3: Yelp vs Amazon').text,
        'No result entered')
    self.assertEqual(xpath(block_xpath_fmt % 'Match 4: Microsoft vs Google').text,
        'No result entered')

    replay_link = wd.find_element_by_link_text('replay').get_attribute('href')
    self.assertTrue(('/' + TEST_REPLAY_SHA1 + '/') in replay_link)

    with contextlib.closing(urllib2.urlopen(replay_link)) as handle:
      self.assertEqual(hashlib.sha1(handle.read()).hexdigest(), TEST_REPLAY_SHA1)

    replay_pack_link = wd.find_element_by_link_text('Replay Pack').get_attribute('href')

    with contextlib.closing(urllib2.urlopen(replay_pack_link)) as handle:
      replay_pack = handle.read()
    zfile = zipfile.ZipFile(cStringIO.StringIO(replay_pack))
    with contextlib.closing(zfile.open('AHGL_S2_Week-1/Match-1_Twitter-Zynga/Twitter-Zynga_1_implausible-ShamWOW.SC2Replay')) as handle:
      self.assertEqual(hashlib.sha1(handle.read()).hexdigest(), TEST_REPLAY_SHA1)

    wd.get(bu)


if __name__ == '__main__':
  unittest.main()
