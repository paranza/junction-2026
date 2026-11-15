from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from server import inspection_cache as cache


class InterruptedInspectionCache(unittest.TestCase):
    def test_only_audited_tiles_resume_and_other_sources_or_policies_do_not_reuse(self):
        with tempfile.TemporaryDirectory() as root,patch.object(cache.store,'RUNTIME',Path(root)):
            identity={'source':'sha-a','question':'How many chairs?','model':'m','policy':{'thinking':'high'}}
            first=cache.InspectionCache(identity);left={'core':[0,0,.5,1]};right={'core':[.5,0,1,1]}
            first.put(left,{'complete':True,'items':[{'label':'Seat','bbox':[.1,.1,.2,.2]}]})
            first.put(right,{'complete':False,'items':[]})
            resumed=cache.InspectionCache(identity)
            self.assertEqual(resumed.get(left)['items'][0]['label'],'Seat')
            self.assertIsNone(resumed.get(right))
            for change in ({'source':'sha-b'},{'question':'How many doors?'},{'model':'other'},
                           {'policy':{'thinking':'medium'}}):
                self.assertIsNone(cache.InspectionCache({**identity,**change}).get(left))
            self.assertEqual(first.path(left).stat().st_mode & 0o777,0o600)

    def test_corrupt_cache_is_ignored_without_becoming_an_answer(self):
        with tempfile.TemporaryDirectory() as root,patch.object(cache.store,'RUNTIME',Path(root)):
            item=cache.InspectionCache({'source':'sha','question':'Q'})
            item.root.mkdir(parents=True);item.path('tile').write_text('{broken')
            self.assertIsNone(item.get('tile'))
