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
    'lidar.yaml': ['sllidar_node'],
}


@pytest.mark.parametrize('file_name,nodes', EXPECTED.items())
def test_param_file_has_a_section_per_node(file_name, nodes):
    with open(os.path.join(PARAM_DIR, file_name)) as f:
        data = yaml.safe_load(f)
    missing = [n for n in nodes if n not in data]
    assert not missing, f'{file_name} is missing sections: {missing}'


def test_lidar_matches_rplidar_c1_datasheet():
    with open(os.path.join(PARAM_DIR, 'lidar.yaml')) as f:
        params = yaml.safe_load(f)['sllidar_node']['ros__parameters']
    assert params['serial_baudrate'] == 460800
    assert params['angle_compensate'] is True
