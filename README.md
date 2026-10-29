# MTRB — ROS 2 Jazzy workspace

iRobot Create 3 (firmware I.0.0.CycloneDDS, namespace `/r2`, dominio 21) + un LiDAR 2D, con Nav2.
Se desarrolla en macOS y se despliega en una Raspberry Pi 5 (ROS 2 Jazzy nativo, sin Docker).

```
src/
├── mtrb_description/            # modelo del robot (solo cinemática y visual, sin simulación)
│   ├── urdf/mtrb.urdf.xacro     # entrada: LiDAR (args lidar_*) + Create 3 opcional
│   ├── urdf/create3_body…, bumper…, wheel…, caster…, common_properties…
│   └── test/test_urdf.py
└── mtrb_bringup/
    ├── launch/mtrb.launch.py    # único launch, mode:=map|mapping; una función por subsistema
    ├── param/{nav2,ekf,slam_toolbox}.yaml
    ├── map/
    ├── mtrb_bringup/utils.py                    # helpers puros (sin ROS), compartidos y testeados
    ├── mtrb_bringup/initial_pose_publisher.py   # publica la pose del dock en /r2/initialpose
    └── test/                    # unitarias, integración y lint
env.sh
```

Arquitectura del launch: `_launch_setup` lee los argumentos (`Settings`) y decide qué arrancar;
cada subsistema (`_state_publisher`, `_ekf`, `_localization`, `_slam`, `_navigation`) devuelve
sus acciones. Todos los nodos se crean con `_node()`, que aplica namespace, remapeo de TF y
`use_sim_time`. Para añadir un subsistema: escribe una función nueva y añádela en `_launch_setup`.

## 1. Instalación y primera configuración

Sigue los pasos en orden la primera vez. Después, en el día a día, solo necesitas el paso 1.6
(`source env.sh`) y el apartado 2 (lanzar).

### 1.1 Requisitos

| Equipo | Qué necesita |
| --- | --- |
| Raspberry Pi 5 | Ubuntu 24.04 (64 bits) + [ROS 2 Jazzy](https://docs.ros.org/en/jazzy/Installation/Ubuntu-Install-Debs.html) (`ros-jazzy-ros-base` basta), `git` |
| iRobot Create 3 | Firmware **I.0.0.CycloneDDS** (o cualquier `I.x` con CycloneDDS) |
| LiDAR 2D | Su driver de ROS 2 instalado en la Pi (no viene en este repositorio) |
| Red | Pi y Create 3 en la **misma red Wi-Fi**, con multicast permitido |

### 1.2 Clonar el repositorio

La raíz del repositorio **es** el workspace de ROS 2 (contiene `src/`), así que se clona
directamente con el nombre que quieras darle al workspace:

```bash
sudo apt install -y git
git clone <URL-del-repositorio> ~/mtrb_ws
cd ~/mtrb_ws
```

Para actualizar más adelante: `cd ~/mtrb_ws && git pull` y vuelve a compilar (paso 1.5).

### 1.3 Instalar las dependencias

```bash
source /opt/ros/jazzy/setup.bash

# Solo la primera vez en esta máquina (si ya lo hiciste, 'rosdep init' da un aviso: ignóralo)
sudo apt install -y python3-rosdep python3-colcon-common-extensions
sudo rosdep init
rosdep update

# Dependencias del proyecto (Nav2, slam_toolbox, robot_localization, xacro, CycloneDDS…)
cd ~/mtrb_ws
rosdep install --from-paths src --ignore-src -r -y
```

`rosdep` lee los `package.xml` e instala todo lo que falta. Si prefieres hacerlo a mano:

```bash
sudo apt install ros-jazzy-navigation2 ros-jazzy-nav2-bringup ros-jazzy-slam-toolbox \
  ros-jazzy-robot-localization ros-jazzy-rmw-cyclonedds-cpp ros-jazzy-xacro
```

### 1.4 Configurar el Create 3

El robot debe usar el **mismo namespace, dominio y middleware** que la Pi; si no, no se ven.

1. Conecta el robot a tu Wi-Fi (solo la primera vez): mantén pulsados los botones **1 y 2**
   hasta que el anillo de luz se ponga azul, conéctate a la red `Create-XXXX` y abre
   `http://192.168.10.1` → *Connect* → elige tu Wi-Fi.
2. Abre la web del robot en su IP de tu red (`http://<ip-del-robot>`) → *Application* →
   *Configuration* y pon:

   | Ajuste | Valor |
   | --- | --- |
   | ROS 2 Domain ID | `21` |
   | ROS 2 Namespace | `/r2` |
   | RMW Implementation | `rmw_cyclonedds_cpp` |

3. Guarda y reinicia la aplicación (*Application* → *Restart Application*).

Si cambias el namespace o el dominio, cámbialos también aquí: `namespace:=` en el launch y
`ROS_DOMAIN_ID` en [env.sh](env.sh).

### 1.5 Compilar

```bash
cd ~/mtrb_ws
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install
```

`--symlink-install` hace que los cambios en YAML, launch y Python se apliquen sin recompilar.
Recompila si añades archivos nuevos o tocas `setup.py`, `package.xml` o `CMakeLists.txt`.

### 1.6 Cargar el entorno (en cada terminal)

```bash
cd ~/mtrb_ws
source env.sh
```

[env.sh](env.sh) fija `ROS_DOMAIN_ID=21` y `RMW_IMPLEMENTATION=rmw_cyclonedds_cpp` y carga ROS 2
y el workspace. Sin esto la Pi no ve al robot. Para no tener que escribirlo cada vez:

```bash
echo 'source ~/mtrb_ws/env.sh' >> ~/.bashrc
```

### 1.7 Comprobar la conexión con el robot

```bash
ros2 topic list | grep /r2
```

Deben aparecer al menos `/r2/odom`, `/r2/imu`, `/r2/tf`, `/r2/tf_static` y `/r2/cmd_vel`.
Si no sale nada:

- Revisa que Pi y robot estén en la misma red y que `echo $ROS_DOMAIN_ID` dé `21`.
- Comprueba que el robot tenga la configuración del paso 1.4.
- Reinicia el daemon de ROS: `ros2 daemon stop && ros2 daemon start`.
- Si tu red bloquea multicast (redes de universidad o empresa), configura `CYCLONEDDS_URI`
  con la IP del robot como peer (ver apartado 4).

### 1.8 LiDAR

El driver del LiDAR **no** está incluido: lánzalo en otra terminal (con `source env.sh`) de modo
que:

- publique en `/r2/scan` (o pasa otro nombre con `scan_topic:=` al launch), y
- su `frame_id` sea igual a `lidar_frame` (por defecto `laser`).

Comprueba con `ros2 topic hz /r2/scan`. Mide la posición del LiDAR respecto al centro del robot
y pásala con `lidar_x`, `lidar_y`, `lidar_z` y `lidar_yaw` (ver TODO).

### 1.9 Desarrollo en macOS (opcional)

En el Mac no hace falta ROS para editar y pasar las pruebas que no dependen de él:

```bash
git clone <URL-del-repositorio> mtrb_ws && cd mtrb_ws
python3 -m venv .venv && source .venv/bin/activate
pip install pytest pyyaml flake8
pytest src/mtrb_bringup/test/test_utils.py src/mtrb_bringup/test/test_params.py
```

Las demás pruebas (`colcon test`) se corren en la Pi.

## 2. Lanzar

Nunca AMCL y slam_toolbox a la vez; el launch lanza solo uno según `mode`.

```bash
# Localizar sobre un mapa existente (pose inicial = dock)
ros2 launch mtrb_bringup mtrb.launch.py mode:=map map:=<ruta/mapa.yaml> \
  dock_x:=0.0 dock_y:=0.0 dock_yaw:=0.0

# Mapa nuevo (el robot arranca en el dock; el origen del mapa es esa pose)
ros2 launch mtrb_bringup mtrb.launch.py mode:=mapping

# Ampliar un mapa guardado (base del pose-graph, sin extensión)
ros2 launch mtrb_bringup mtrb.launch.py mode:=mapping posegraph:=<ruta/base> \
  dock_x:=… dock_y:=… dock_yaw:=…
```

Argumentos útiles: `namespace` (r2), `navigation` (false = solo localizar/mapear), `use_ekf`,
`scan_topic`, `odom_topic`, `imu_topic`, `lidar_frame`, `lidar_x/y/z/yaw`, `params_file`,
`ekf_params_file`, `slam_params_file`, `use_sim_time`. Ver `ros2 launch mtrb_bringup mtrb.launch.py -s`.
Sin `map:=` se busca `map/map.yaml` del paquete instalado.

Guardar mapas (con `mode:=mapping` en marcha; el directorio debe existir):
```bash
ros2 service call /r2/slam_toolbox/save_map slam_toolbox/srv/SaveMap "{name: {data: '<ruta/base>'}}"
ros2 service call /r2/slam_toolbox/serialize_map slam_toolbox/srv/SerializePoseGraph "{filename: '<ruta/base>'}"
```
Guarda ambos: `.yaml/.pgm` para `mode:=map` y `.posegraph/.data` para ampliar.

Visualización: se hará desde una interfaz web (pendiente). No se usa RViz.

## 3. Namespace y remapeos

Todos los nodos van en `/r2`. Los topics relativos se resuelven bajo `/r2`.

| Nodo | Remapeo | Efecto |
| --- | --- | --- |
| todos (Nav2, AMCL, map_server, EKF, slam_toolbox, robot_state_publisher) | `/tf → tf`, `/tf_static → tf_static` | usan `/r2/tf`, `/r2/tf_static` del Create 3 |
| robot_state_publisher (`mtrb_state_publisher`) | `robot_description → mtrb_description` | no choca con `/r2/robot_description` del robot |
| EKF | `odom → odom_topic`, `imu → imu_topic` | entradas `/r2/odom`, `/r2/imu`; salida `/r2/odometry/filtered` |
| controller_server, behavior_server | `cmd_vel → cmd_vel_nav` | |
| velocity_smoother | `cmd_vel → cmd_vel_nav`, `cmd_vel_smoothed → cmd_vel` | salida final `/r2/cmd_vel` (`Twist`) |
| Nav2 / AMCL / slam_toolbox | `scan_topic` (parámetro, no remap) | `/r2/scan` por defecto |

- `odom → base_link` lo publica el Create 3. El EKF corre con `publish_tf: false` (dos publicadores
  romperían el árbol TF); su `/r2/odometry/filtered` la usan controller, bt_navigator y velocity_smoother.
  AMCL y los costmaps usan el TF crudo del robot.
- El launch publica solo `base_link → <lidar_frame>`; el resto del TF del Create 3 viene del robot.
- Pose del dock: en `map` se publica una vez en `/r2/initialpose` cuando AMCL está activo. En `mapping`
  sin pose-graph, el origen del mapa es la pose del robot al arrancar (el dock); con pose-graph se
  pasa `dock_*` como `map_start_pose` de slam_toolbox.

## 4. Compatibilidad Iron (robot) / Jazzy (Pi)

- Los topics estándar (`odom`, `imu`, `tf`, `cmd_vel`, `scan`) no dependen de la distro.
- Los mensajes propios (`irobot_create_msgs`) tienen tipos de Iron: no se usan aquí, pero si los añades
  verifica con `ros2 interface show` que coinciden con los del firmware.
- Nav2 en Jazzy publica `cmd_vel` como `Twist` (sin stamp), que es lo que espera el Create 3. Si un
  cambio de versión lo pasara a `TwistStamped`, el robot dejaría de moverse sin error visible.
- Ambos lados deben usar `rmw_cyclonedds_cpp` y `ROS_DOMAIN_ID=21`; sin multicast, hay que configurar
  `CYCLONEDDS_URI` con peers explícitos.

## 5. Pruebas y estilo

```bash
colcon build --symlink-install && source env.sh
colcon test && colcon test-result --verbose
```

- `mtrb_bringup/test/`: `test_utils.py` y `test_initial_pose.py` (unitarias), `test_params.py`
  (cada nodo del launch tiene su sección en el YAML), `test_launch.py` (argumentos públicos),
  `test_flake8.py` y `test_pep257.py` (estilo).
- `mtrb_description/test/test_urdf.py`: el xacro genera los frames esperados y nada de simulación.
- Estilo: el de ROS 2 (`ament_flake8`, líneas de 99, config en `mtrb_bringup/setup.cfg`).
  `test_utils.py` y `test_params.py` corren también sin ROS: `pytest src/mtrb_bringup/test`.

## 6. Cómo contribuir

1. Cambios de comportamiento → primero en los YAML de `param/`; en el launch solo si hace falta
   un nodo o argumento nuevo (y documenta el argumento arriba).
2. Lógica nueva sin dependencias de ROS → `mtrb_bringup/utils.py` con su prueba en `test_utils.py`.
3. Nodo nuevo → archivo propio en `mtrb_bringup/`, entrada en `setup.py`, dependencias en
   `package.xml`, y su sección en el YAML (añádela a `test_params.py`).
4. Antes de subir: `colcon test` sin fallos.

## 7. TODO

`grep -rn TODO src/`: pose real del LiDAR (`lidar_*`), rangos mín/máx del LiDAR (AMCL, slam, costmaps),
tuning de inflación/velocidades.
