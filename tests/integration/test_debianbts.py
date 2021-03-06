#!/usr/bin/env python
# -*- coding: utf-8 -*-

# debianbts_test.py - Unittests for debianbts.py.
# Copyright (C) 2009  Bastian Venthur <venthur@debian.org>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.


from __future__ import division, unicode_literals, absolute_import

import datetime
import email.message
import math
import random
import logging
try:
    import unittest.mock as mock
except ImportError:
    import mock

import pytest

from pysimplesoap.simplexml import SimpleXMLElement

import debianbts as bts

logger = logging.getLogger(__name__)


@pytest.fixture
def create_bugreport():
    def factory(**kwargs):
        bugreport = bts.Bugreport()
        bugreport.severity = 'normal'
        for k, v in kwargs.items():
            setattr(bugreport, k, v)
        return bugreport
    return factory


def test_get_usertag_empty():
    """get_usertag should return empty dict if no bugs are found."""
    d = bts.get_usertag("thisisatest@debian.org")
    assert d == dict()


def test_get_usertag():
    """get_usertag should return dict with tag(s) and buglist(s)."""
    d = bts.get_usertag("debian-python@lists.debian.org")
    assert isinstance(d, dict)
    for k, v in d.items():
        assert is_unicode(k)
        assert isinstance(v, list)
        for bug in v:
            assert isinstance(bug, int)


def test_get_usertag_filters():
    """get_usertag should return only requested tags"""
    tags = bts.get_usertag("debian-python@lists.debian.org")
    assert isinstance(tags, dict)
    randomKey0 = random.choice(list(tags.keys()))
    randomKey1 = random.choice(list(tags.keys()))

    filtered_tags = bts.get_usertag(
        "debian-python@lists.debian.org", randomKey0, randomKey1)

    assert len(filtered_tags) == 2
    assert set(filtered_tags[randomKey0]) == set(tags[randomKey0])
    assert set(filtered_tags[randomKey1]) == set(tags[randomKey1])


def test_get_bugs_empty():
    """get_bugs should return empty list if no matching bugs where found."""
    bugs = bts.get_bugs("package", "thisisatest")
    assert bugs == []


def test_get_bugs():
    """get_bugs should return list of bugnumbers."""
    bugs = bts.get_bugs("submitter", "venthur@debian.org")
    assert len(bugs) != 0
    assert isinstance(bugs, list)
    for i in bugs:
        assert isinstance(i, int)


def test_get_bugs_list():
    """older versions of python-debianbts accepted malformed key-val-lists."""
    bugs = bts.get_bugs(
            'submitter',
            'venthur@debian.org',
            'severity',
            'normal')
    bugs2 = bts.get_bugs(
            ['submitter', 'venthur@debian.org', 'severity', 'normal'])
    assert len(bugs) != 0
    bugs.sort()
    bugs2.sort()
    assert bugs == bugs2


def test_newest_bugs():
    """newest_bugs should return list of bugnumbers."""
    bugs = bts.newest_bugs(10)
    assert isinstance(bugs, list)
    for i in bugs:
        assert isinstance(i, int)


def test_newest_bugs_amount():
    """newest_bugs(amount) should return a list of len 'amount'. """
    for i in 0, 1, 10:
        bugs = bts.newest_bugs(i)
        assert len(bugs) == i


def test_get_bug_log():
    """get_bug_log should return the correct data types."""
    bl = bts.get_bug_log(223344)
    assert isinstance(bl, list)
    for i in bl:
        assert isinstance(i, dict)
        assert "attachments" in i
        assert isinstance(i["attachments"], list)
        assert "body" in i
        assert is_unicode(i["body"])
        assert "header" in i
        assert is_unicode(i["header"])
        assert "msg_num" in i
        assert isinstance(i["msg_num"], int)


def test_get_bug_log_with_attachments():
    """get_bug_log should include attachments"""
    buglogs = bts.get_bug_log(400000)
    for bl in buglogs:
        assert "attachments" in bl


def test_bug_log_message():
    """dict returned by get_bug_log has a email.Message field"""
    buglogs = bts.get_bug_log(400012)
    for buglog in buglogs:
        assert 'message' in buglog
        msg = buglog['message']
        assert isinstance(msg, email.message.Message)
        assert 'Subject' in msg
        if not msg.is_multipart():
            assert is_unicode(msg.get_payload())


def test_bug_log_message_unicode():
    """test parsing of bug_log mail with non ascii characters"""
    buglogs = bts.get_bug_log(773321)
    buglog = buglogs[2]
    msg_payload = buglog['message'].get_payload()
    assert is_unicode(msg_payload)
    assert 'é' in msg_payload


def test_empty_get_status():
    """get_status should return empty list if bug doesn't exits"""
    bugs = bts.get_status(0)
    assert isinstance(bugs, list)
    assert len(bugs) == 0


def test_sample_get_status():
    """test retrieving of a "known" bug status"""
    bugs = bts.get_status(486212)
    assert len(bugs) == 1
    bug = bugs[0]
    assert bug.bug_num == 486212
    assert bug.date == datetime.datetime(2008, 6, 14, 10, 30, 2)
    assert bug.subject.startswith('[reportbug-ng] segm')
    assert bug.package == 'reportbug-ng'
    assert bug.severity == 'normal'
    assert bug.tags == ['help']
    assert bug.blockedby == []
    assert bug.blocks == []
    assert bug.summary == ''
    assert bug.location == 'archive'
    assert bug.source == 'reportbug-ng'
    assert bug.log_modified == datetime.datetime(2008, 8, 17, 7, 26, 22)
    assert bug.pending == 'done'
    assert bug.done
    assert bug.archived
    assert bug.found_versions == ['reportbug-ng/0.2008.06.04']
    assert bug.fixed_versions == ['reportbug-ng/1.0']
    assert bug.affects == []


def test_bug_str(create_bugreport):
    """test string conversion of a Bugreport"""
    b1 = create_bugreport(package='foo-pkg', bug_num=12222)
    s = str(b1)
    assert isinstance(s, str)  # byte string in py2, unicode in py3
    assert 'bug_num: 12222\n' in s
    assert 'package: foo-pkg\n' in s


def test_get_status_affects():
    """test a bug with "affects" field"""
    bugs = bts.get_status(290501, 770490)
    assert len(bugs) == 2
    assert bugs[0].affects == []
    assert bugs[1].affects == ['conkeror']


@mock.patch.object(bts.debianbts, '_build_soap_client')
def test_status_batches_large_bug_counts(mock_build_client):
    """get_status should perform requests in batches to reduce server load."""
    mock_build_client.return_value = mock_client = mock.Mock()
    mock_client.call.return_value = SimpleXMLElement(
        '<a><s-gensym3/></a>')
    nr = bts.BATCH_SIZE + 10.0
    calls = int(math.ceil(nr / bts.BATCH_SIZE))
    bts.get_status([722226] * int(nr))
    assert mock_client.call.call_count == calls


@mock.patch.object(bts.debianbts, '_build_soap_client')
def test_status_batches_multiple_arguments(mock_build_client):
    """get_status should batch multiple arguments into one request."""
    mock_build_client.return_value = mock_client = mock.Mock()
    mock_client.call.return_value = SimpleXMLElement(
        '<a><s-gensym3/></a>')
    batch_size = bts.BATCH_SIZE

    calls = 1
    bts.get_status(*list(range(batch_size)))
    assert mock_client.call.call_count == calls

    calls += 2
    bts.get_status(*list(range(batch_size + 1)))
    assert mock_client.call.call_count == calls


def test_comparison(create_bugreport):
    """comparison of two bugs"""
    b1 = create_bugreport(archived=True)
    b2 = create_bugreport(done=True)
    assert b2 > b1
    assert b2 >= b1
    assert b2 != b1
    assert not(b2 == b1)
    assert not(b2 <= b1)
    assert not(b2 < b1)


def test_comparison_equal(create_bugreport):
    """comparison of two bug which are equal regarding their
    relative order"""
    b1 = create_bugreport(done=True)
    b2 = create_bugreport(done=True)
    assert not(b2 > b1)
    assert b2 >= b1
    assert b2 == b1
    assert not(b2 < b1)
    assert b2 <= b1


def test_get_bugs_int_bugs():
    """It is possible to pass a list of bug number to get_bugs"""
    bugs = bts.get_bugs('bugs', [400010, 400012], 'archive', True)
    assert set(bugs) == set((400010, 400012))


def test_get_bugs_single_int_bug():
    """bugs parameter in get_bugs can be a list of int or a int"""
    bugs1 = bts.get_bugs('bugs', 400040, 'archive', True)
    bugs2 = bts.get_bugs('bugs', [400040], 'archive', True)
    assert bugs1 == bugs2


def test_mergedwith():
    """Mergedwith is always a list of int."""
    # this one is merged with two other bugs
    m = bts.get_status(486212)[0].mergedwith
    assert len(m) == 2
    for i in m:
        assert isinstance(i, int)
    # this one was merged with one bug
    m = bts.get_status(433550)[0].mergedwith
    assert len(m) == 1
    assert isinstance(m[0], int)
    # this one was not merged
    m = bts.get_status(474955)[0].mergedwith
    assert m == list()


def test_base64_status_fields():
    """fields in bug status are sometimes base64-encoded"""
    bug = bts.get_status(711111)[0]
    assert is_unicode(bug.originator)
    assert bug.originator.endswith('gmail.com>')
    assert 'ł' in bug.originator


def test_base64_buglog_body():
    """buglog body is sometimes base64 encoded"""
    buglog = bts.get_bug_log(773321)
    body = buglog[2]['body']
    assert is_unicode(buglog[1]['body'])
    assert 'é' in body


def test_string_status_originator():
    """test reading of bug status originator that is not base64-encoded"""
    bug = bts.get_status(711112)[0]
    assert is_unicode(bug.originator)
    assert bug.originator.endswith('debian.org>')


def test_unicode_conversion_in_str():
    """string representation must deal with unicode correctly."""
    [bug] = bts.get_status(773321)
    try:
        bug.__str__()
    except UnicodeEncodeError:
        pytest.fail()


def test_regression_588954():
    """Get_bug_log must convert the body correctly to unicode."""
    try:
        bts.get_bug_log(582010)
    except UnicodeDecodeError:
        pytest.fail()


def test_version():
    assert isinstance(bts.__version__, str)


def test_regression_590073():
    """bug.blocks is sometimes a str sometimes an int."""
    try:
        # test the int case
        # TODO: test the string case
        bts.get_status(568657)
    except TypeError:
        pytest.fail()


def test_regression_590725():
    """bug.body utf sometimes contains invalid continuation bytes."""
    try:
        bts.get_bug_log(578363)
        bts.get_bug_log(570825)
    except UnicodeDecodeError:
        pytest.fail()


def test_regression_670446():
    """affects should be split by ','"""
    bug = bts.get_status(657408)[0]
    assert bug.affects == ['epiphany-browser-dev', 'libwebkit-dev']


def test_regression_799528():
    """fields of buglog are sometimes base64 encoded."""
    # bug with base64 encoding originator
    [bug] = bts.get_status(711111)
    assert 'ł' in bug.originator
    # bug with base64 encoding subject
    [bug] = bts.get_status(779005)
    assert '‘' in bug.subject


def is_unicode(string):
    """asserts for type of a unicode string, depending on python version"""
    if bts.PY2:
        return isinstance(string, unicode) # noqa
    else:
        return isinstance(string, str)
