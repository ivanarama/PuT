"""Real OneBase export contract: all 17 kinds, excluded orders, dates and basis closure."""
from pathlib import Path
import argparse,datetime,json,subprocess,tempfile
import yaml

ROOT=Path(__file__).resolve().parents[1]
EXCLUDED={'ЗаказПокупателя','ЗаказПоставщику','ЗакрытиеЗаказовПокупателей','ЗакрытиеЗаказовПоставщикам'}

def main():
    p=argparse.ArgumentParser();p.add_argument('--onebase',required=True);p.add_argument('--output',type=Path);a=p.parse_args()
    binary=str(Path(a.onebase).resolve())
    with tempfile.TemporaryDirectory(prefix='put-bp3-contract-') as tmp:
        tmp=Path(tmp);db=tmp/'fixture.db'
        def run(*args,ok=True):
            r=subprocess.run([binary,*args,'--project',str(ROOT),'--sqlite',str(db),'--no-gui'],cwd=ROOT,capture_output=True,text=True,encoding='utf-8',timeout=120)
            assert (r.returncode==0)==ok,r.stdout+r.stderr
            return r
        def export(name,**options):
            f=tmp/(name+'.json');args=['procrun','--proc','ВыгрузкаБП3','--set','Путь='+str(f)]
            for key,value in options.items():args+=['--set',key+'='+value]
            run(*args);return json.loads(f.read_text(encoding='utf-8-sig'))
        run('migrate');run('procrun','--proc','ЗаполнитьТестовуюБазу')
        initial=export('initial')
        initial_path=tmp/'initial.json'
        subprocess.run(['python',str(ROOT/'scripts/prepare_bp3_fixture.py'),'--onebase',binary,'--project',str(ROOT),'--database',str(db),'--dump',str(initial_path)],check=True,capture_output=True)
        full=export('full')
        assert full['format']=='OneBase-PuT-BP3' and full['version']=='1.0'
        assert full['sourceId']=='PuT'
        assert all(not full['documents'][k] for k in EXCLUDED)
        assert len([k for k,v in full['documents'].items() if v])==17
        entities=[yaml.safe_load(f.read_text(encoding='utf-8-sig')) for f in (ROOT/'documents').glob('*.yaml')]
        definitions={e['name']:e for e in entities}
        index={(k,r['uid']):r for k,rows in full['documents'].items() for r in rows}
        refs={k:[(f['name'],f['type'].split(':',1)[1]) for f in e.get('fields',[]) if f.get('type','').startswith('reference:') and f['type'].split(':',1)[1] in definitions and f['type'].split(':',1)[1] not in EXCLUDED] for k,e in definitions.items()}
        def closure(selected):
            expected=set(selected);pending=list(selected)
            while pending:
                key=pending.pop();row=index[key]
                for field,kind in refs[key[0]]:
                    if not row.get(field):continue
                    basis=(kind,row[field]);assert basis in index,basis
                    if basis not in expected:expected.add(basis);pending.append(basis)
            return expected
        def keys(d):return {(k,r['uid']) for k,rs in d['documents'].items() for r in rs}
        posted=export('posted',ТолькоПроведенные='true')
        assert keys(posted)==closure(k for k,r in index.items() if r['posted'])
        # Select a day with an older basis, so a plain date filter cannot pass.
        day=next(row['Дата'][:10] for key,row in index.items() for field,kind in refs[key[0]] if row.get(field) and index[(kind,row[field])]['Дата'][:10]!=row['Дата'][:10])
        window=export('window',ДатаНачала=day,ДатаОкончания=day)
        chosen={k for k,r in index.items() if r['Дата'][:10]==day}
        assert keys(window)==closure(chosen) and len(keys(window))>len(chosen)
        for kind,rows in window['documents'].items():
            for row in rows:assert row['dependency']==((kind,row['uid']) not in chosen)
        run('procrun','--proc','ВыгрузкаБП3','--set','Путь='+str(tmp/'bad.json'),'--set','ДатаНачала=28.10.2026',ok=False)
        assert not (tmp/'bad.json').exists()
        result={'ok':True,'documents':len(index),'kinds':17,'excluded':sorted(EXCLUDED),'posted_with_bases':len(keys(posted)),'period_selected':len(chosen),'period_with_bases':len(keys(window))}
        if a.output:a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps(result,ensure_ascii=False))

if __name__=='__main__':main()
