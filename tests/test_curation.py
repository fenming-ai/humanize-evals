import csv
import copy
import tempfile
import unittest
from pathlib import Path
from tools.curation_audit import audit, sha

class Curation(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        text='共12人参加，其中8人完成。暂未统计错误率。'
        with (self.root/'source.csv').open('w') as f:
            w=csv.DictWriter(f,fieldnames=['id','text']);w.writeheader();w.writerow({'id':'1','text':text})
        self.case={'id':'c1','text':text,'category':'facts','split':'development','group_id':'g1',
                   'review_status':'model_accepted','provenance':{'file':'source.csv','csv_record':1,'id':'1',
                   'text_sha256':sha(text),'domain':'synthetic-test','generator':'fixture'},
                   'checks':[{'quote':'12人参加','requirement':'保留参加人数'}],
                   'voice_quote':'暂未统计','failure_conditions':['把8人改成全部人','声称统计错误率'],
                   'allowed_changes':['调整标点'],'audience':'测试读者'}
    def tearDown(self):self.tmp.cleanup()
    def test_valid_source(self):self.assertEqual(audit([self.case],self.root)['cases'],1)
    def test_invalid_quote_and_changed_source(self):
        for field,value in [('text','改变的正文'),('voice_quote','原文不存在')]:
            row=copy.deepcopy(self.case);row[field]=value
            with self.assertRaises(ValueError):audit([row],self.root)
    def test_group_leakage(self):
        row=copy.deepcopy(self.case);row['id']='c2';row['split']='holdout'
        with self.assertRaises(ValueError):audit([self.case,row],self.root)
    def test_empty_and_unreviewed(self):
        with self.assertRaises(ValueError):audit([],self.root)
        self.case['review_status']='candidate'
        with self.assertRaises(ValueError):audit([self.case],self.root)
    def test_path_escape(self):
        self.case['provenance']['file']='../outside.csv'
        with self.assertRaises(ValueError):audit([self.case],self.root)
