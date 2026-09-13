import json
import threading
from http.server import ThreadingHTTPServer

import pytest

from mib_runner.agents import ReferenceMemoryAgent
from mib_runner.cli import main, build_parser
from mib_runner.report import verify_score
from mib_runner.server import make_http_handler
from paths import DEV_PACK, SCENARIO_SCHEMA_PATH, REPORT_SCHEMA_PATH


def test_public_benchmark_submission_uses_real_http_adapter(tmp_path, monkeypatch):
    import mib_runner.cli as cli
    real_build = cli.build_submission_runtime
    runtime_options = {}
    def build_runtime(*args, **kwargs):
        runtime_options.update(kwargs)
        return real_build(*args, **kwargs)
    monkeypatch.setattr(cli, 'build_submission_runtime', build_runtime)
    server = ThreadingHTTPServer(('127.0.0.1', 0), make_http_handler(ReferenceMemoryAgent))
    thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
    template = json.loads((DEV_PACK/'epistemic/MIB-EPI-002.json').read_text())
    profile = {'id':'http-cli','version':'0.1.0','required_templates':[template['id']],
        'dimensions':{d:{'weight':1/len(template['dimensions'])} for d in template['dimensions']}}
    profile_path=tmp_path/'profile.json';profile_path.write_text(json.dumps(profile))
    spec=tmp_path/'submission.json';spec.write_text(json.dumps({'id':'http-cli','transport':'http','base_url':f'http://127.0.0.1:{server.server_port}'}))
    output=tmp_path/'report.json'
    try:
        assert main(['benchmark',str(DEV_PACK/'epistemic/MIB-EPI-002.json'),'--profile',str(profile_path),
            '--schema',str(SCENARIO_SCHEMA_PATH),'--report-schema',str(REPORT_SCHEMA_PATH),
            '--submission',str(spec),'--seeds','101','--repetitions','1','--bootstrap-resamples','0',
            '--output-report',str(output)]) == 0
        report=json.loads(output.read_text())
        assert report['report_version']=='0.4.0'
        assert verify_score(report)['valid']
        assert report['execution']['execution_failure_rate']==0
        assert report['efficiency']['participant_reported']['total_cost'] is None
        assert runtime_options['confine_stage_to_spec_dir'] is True
        assert str(profile_path.resolve()) in runtime_options['hide_paths']
        assert str((DEV_PACK/'epistemic/MIB-EPI-002.json').resolve()) in runtime_options['hide_paths']
    finally:
        server.shutdown();server.server_close();thread.join()


def test_agent_and_submission_flags_are_mutually_exclusive():
    with pytest.raises(SystemExit):
        build_parser().parse_args(['benchmark','--profile','p','--schema','s','--agent','reference','--submission','x'])
