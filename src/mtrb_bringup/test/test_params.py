"""Integration check: every node the launch starts has a section in its YAML file."""

import os

import pytest

yaml = pytest.importorskip('yaml')

PARAM_DIR = os.path.join(os.path.dirname(__file__), '..', 'param')

# Node names used in launch/mtrb.launch.py.
EXPECTED = {
    'nav2.yaml': ['map_server', 'amcl', 'planner_server', 'controller_server',
                  'behavior_server', 'bt_navigator', 'velocity_smoother',
                  'global_costmap', 'local_costmap'],
    'ekf.yaml': ['ekf_filter_node'],
    'slam_toolbox.yaml': ['slam_toolbox'],
}


@pytest.mark.parametrize('file_name,nodes', EXPECTED.items())
def test_param_file_has_a_section_per_node(file_name, nodes):
    with open(os.path.join(PARAM_DIR, file_name)) as f:
        data = yaml.safe_load(f)
    missing = [n for n in nodes if n not in data]
    assert not missing, f'{file_name} is missing sections: {missing}'
