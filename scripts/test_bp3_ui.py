"""Browser verification of managed exporter parameters and its real queued job."""
from pathlib import Path
from urllib.parse import quote
import argparse,json,time
from playwright.sync_api import sync_playwright

def main():
    p=argparse.ArgumentParser();p.add_argument('--url',required=True);p.add_argument('--login',required=True);p.add_argument('--password-file',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--browser',default=r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe');a=p.parse_args()
    # Password file belongs to this isolated fixture and is never copied to evidence.
    text=a.password_file.read_text(encoding='utf-16')
    password=next(line.split(':',1)[1].strip() for line in text.splitlines() if line.startswith('Пароль:'))
    out=a.output.resolve();out.mkdir(parents=True,exist_ok=True);results=[]
    with sync_playwright() as p:
        b=p.chromium.launch(executable_path=a.browser,headless=True);page=b.new_page(viewport={'width':1400,'height':1100})
        page.goto(a.url.rstrip('/')+'/ui/processor/'+quote('выгрузкабп3'))
        page.locator('[name=login]').fill(a.login);page.locator('[name=password]').fill(password);page.get_by_role('button',name='Войти',exact=True).click();page.wait_for_load_state('networkidle')
        assert page.locator('[name=КодИсточника]').count()==1
        assert page.locator('[name=ТолькоПроведенные]').count()==1
        def command(title):
            with page.expect_response(lambda r:'/form-event' in r.url and r.request.method=='POST') as response:
                page.get_by_role('button',name=title,exact=True).click()
            assert response.value.ok
            response.value.body()
            page.wait_for_timeout(250)
        for posted,expected in [(False,42),(True,36)]:
            target=out/('posted.json' if posted else 'all.json');code='PuT.BP3.web.'+str(posted)
            target.unlink(missing_ok=True)
            page.locator('[name=Путь]').fill(str(target));page.locator('[name=КодИсточника]').fill(code)
            page.locator('[name=ТолькоПроведенные]').set_checked(posted)
            page.screenshot(path=str(out/('posted-form.png' if posted else 'all-form.png')),full_page=True)
            command('Поставить в очередь')
            deadline=time.monotonic()+60
            while time.monotonic()<deadline:
                command('Обновить результат')
                state=page.locator('[name=СостояниеЗадачи]').input_value()
                if state=='Выполнено':break
                assert not state.startswith('Ошибка'),page.locator('[name=РезультатЗадачи]').input_value()
                page.wait_for_timeout(500)
            else:raise AssertionError('Queued exporter timed out')
            data=json.loads(target.read_text(encoding='utf-8-sig'));count=sum(len(x) for x in data['documents'].values())
            assert data['sourceId']==code and count==expected,(data['sourceId'],count,expected)
            results.append({'posted_only':posted,'sourceId':code,'documents':count,'state':state})
            page.screenshot(path=str(out/('posted-done.png' if posted else 'all-done.png')),full_page=True)
        b.close()
    (out/'result.json').write_text(json.dumps({'ok':True,'runs':results},ensure_ascii=False,indent=2),encoding='utf-8')
    print('[OK] Managed PuT exporter: queued jobs produced 42/36 documents; source code and posted checkbox preserved')

if __name__=='__main__':main()
