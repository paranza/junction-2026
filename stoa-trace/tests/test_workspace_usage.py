import json
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch
from server import store

class WorkspaceUsageTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.runtime=patch.object(store,'RUNTIME',Path(self.temp.name));self.runtime.start()
        self.data=patch.object(store,'DATA_ROOT',Path(self.temp.name)/'no-dataset');self.data.start()
        store.initialize()
    def tearDown(self):
        self.data.stop();self.runtime.stop();self.temp.cleanup()
    def test_workspace_deduplicates_requests_and_keeps_unpriced_usage_unknown(self):
        attempt={'request_id':'r1','provider':'gemini','model':'unpriced','message_id':'m1'}
        store.record_event('model_request',attempt)
        store.record_event('model_request',attempt)
        response={**attempt,'usage':{'input_tokens':100,'output_tokens':20,'cached_input_tokens':0}}
        store.record_event('model_response',response)
        store.record_event('model_response',response)
        result=store.workspace_usage(7)
        self.assertEqual(result['aggregate']['model_calls'],1)
        self.assertEqual(result['aggregate']['input_tokens'],100)
        self.assertIsNone(result['aggregate']['cost_estimate_usd'])
        self.assertEqual(sum(day['usage']['model_calls'] for day in result['daily']),1)
    def test_missing_and_mismatched_responses_never_become_free(self):
        store.record_event('model_request',{'request_id':'r2','provider':'gemini','model':'unpriced','message_id':'m2'})
        store.record_event('model_response',{'request_id':'r2','provider':'gemini','model':'different','message_id':'m2','usage':{'input_tokens':300,'output_tokens':20}})
        result=store.workspace_usage(7)['aggregate']
        self.assertEqual(result['unknown_usage_calls'],1)
        self.assertIsNone(result['cost_estimate_usd'])
    def test_dataset_and_uploads_are_distinct_even_with_same_name(self):
        with store.connection() as db:
            for i,uploaded in enumerate((0,1)):
                db.execute('INSERT INTO documents(id,path,absolute_path,name,format,source,size,mtime,uploaded) VALUES(?,?,?,?,?,?,?,?,?)',(str(i),str(i),str(i),'plan.pdf','pdf','uploads' if uploaded else 'dataset',1,time.time(),uploaded))
        self.assertEqual(store.list_documents(uploaded=False)['total'],1)
        self.assertEqual(store.list_documents(uploaded=True)['documents'][0]['id'],'1')
    def test_projects_hold_distinct_chats_and_independent_message_sessions(self):
        project=store.create_chat('Residential project',project=True)
        first=store.create_chat('Ground floor',project_id=project)
        second=store.create_chat('First floor',project_id=project)
        self.assertNotEqual(first,second)
        store.record_message_usage(first,'m1',None,'Question A','completed','answer-a')
        store.record_message_usage(second,'m2',None,'Question B','completed','answer-b')
        self.assertEqual(store.session_usage(first)['messages'][0]['question'],'Question A')
        self.assertEqual(store.session_usage(second)['message_count'],1)
        self.assertEqual(len(store.chat_workspace()['threads']),2)
    def test_chat_can_be_renamed_moved_and_ungrouped(self):
        project=store.create_chat('Building',project=True)
        chat=store.create_chat('New chat')
        store.update_chat(chat,title='Kitchen',project_id=project)
        self.assertEqual(store.chat_workspace()['threads'][0]['project_id'],project)
        store.update_chat(chat,project_id='')
        item=store.chat_workspace()['threads'][0]
        self.assertIsNone(item['project_id'])
        self.assertEqual(item['title'],'Kitchen')
    def test_missing_project_cannot_receive_a_chat(self):
        with self.assertRaises(KeyError): store.create_chat('Plan',project_id='missing')
