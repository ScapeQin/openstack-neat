# Copyright 2012 Anton Beloglazov
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from mocktest import *
from pyqcy import *

import os
import shutil
import libvirt
import neat.collector as collector
import neat.db_utils as db_utils


class Collector(TestCase):

    # def setUp(self):
    #     MockTransaction.__enter__()

    # def tearDown(self):
    #     MockTransaction.__exit__()

    @qc(10)
    def start(iterations=int_(0, 10)):
        with MockTransaction:
            expect(collector).collect(any_dict).exactly(iterations).times()
            assert collector.start(iterations) == iterations

    @qc(1)
    def get_previous_vms():
        local_data_directory = os.path.join(
            os.path.dirname(__file__), 'resources', 'vms')
        previous_vms = collector.get_previous_vms(local_data_directory)
        assert 'ec452be0-e5d0-11e1-aff1-0800200c9a66' in previous_vms
        assert 'e615c450-e5d0-11e1-aff1-0800200c9a66' in previous_vms
        assert 'f3e142d0-e5d0-11e1-aff1-0800200c9a66' in previous_vms

    @qc
    def get_current_vms(
        ids=dict_(
            keys=int_(min=0),
            values=str_(of='abc123-', min_length=36, max_length=36),
            min_length=0, max_length=10
        )
    ):
        with MockTransaction:

            def init_vm(id):
                vm = mock('vm')
                expect(vm).UUIDString().and_return(ids[id]).once()
                return vm

            connection = libvirt.virConnect()
            expect(connection).listDomainsID().and_return(ids.keys()).once()
            if ids:
                expect(connection).lookupByID(any_int) \
                    .and_call(lambda id: init_vm(id))
            assert collector.get_current_vms(connection) == ids.values()

    @qc
    def build_local_vm_path(
        x=str_(of='abc123_-/')
    ):
        assert collector.build_local_vm_path(x) == os.path.join(x, 'vms')

    @qc
    def get_added_vms(
        x=list_(
            of=str_(of='abc123-', min_length=36, max_length=36),
            min_length=0, max_length=5
        ),
        y=list_(
            of=str_(of='abc123-', min_length=36, max_length=36),
            min_length=0, max_length=5
        )
    ):
        previous_vms = list(x)
        if x:
            x.pop(random.randrange(len(x)))
        x.extend(y)
        assert set(collector.get_added_vms(previous_vms, x)) == set(y)

    @qc
    def get_removed_vms(
        x=list_(
            of=str_(of='abc123-', min_length=36, max_length=36),
            min_length=0, max_length=5
        ),
        y=list_(
            of=str_(of='abc123-', min_length=36, max_length=36),
            min_length=0, max_length=5
        )
    ):
        previous_vms = list(x)
        removed = []
        if x:
            to_remove = random.randrange(len(x))
            for _ in xrange(to_remove):
                removed.append(x.pop(random.randrange(len(x))))
        x.extend(y)
        assert set(collector.get_removed_vms(previous_vms, x)) == set(removed)

    @qc
    def substract_lists(
        x=list_(of=int_(min=0, max=20), max_length=10),
        y=list_(of=int_(min=0, max=20), max_length=10)
    ):
        assert set(collector.substract_lists(x, y)) == \
            set([item for item in x if item not in y])

    @qc(1)
    def cleanup_local_data():
        local_data_directory = os.path.join(
            os.path.dirname(__file__), 'resources', 'vms')
        local_data_directory_tmp = os.path.join(
            local_data_directory, 'tmp')
        vm1 = 'ec452be0-e5d0-11e1-aff1-0800200c9a66'
        vm2 = 'e615c450-e5d0-11e1-aff1-0800200c9a66'
        vm3 = 'f3e142d0-e5d0-11e1-aff1-0800200c9a66'
        initial_files = len(os.listdir(local_data_directory_tmp))

        shutil.copy(os.path.join(local_data_directory, vm1),
                    local_data_directory_tmp)
        shutil.copy(os.path.join(local_data_directory, vm2),
                    local_data_directory_tmp)
        shutil.copy(os.path.join(local_data_directory, vm3),
                    local_data_directory_tmp)

        assert len(os.listdir(local_data_directory_tmp)) == initial_files + 3

        collector.cleanup_local_data(local_data_directory_tmp, [vm1, vm2, vm3])

        assert len(os.listdir(local_data_directory_tmp)) == initial_files

    @qc
    def fetch_remote_data(
        x=dict_(
            keys=str_(of='abc123-', min_length=36, max_length=36),
            values=list_(of=int_(min=0, max=3000), min_length=0, max_length=10),
            min_length=0, max_length=3
        ),
        data_length=int_(min=1, max=10)
    ):
        db = db_utils.init_db('sqlite:///:memory:')
        if x:
            for uuid, data in x.items():
                result = db.vms.insert().execute(uuid=uuid)
                vm_id = result.inserted_primary_key[0]
                for mhz in reversed(data):
                    db.vm_resource_usage.insert().execute(
                        vm_id=vm_id,
                        cpu_mhz=mhz)
                x[uuid] = data[:data_length]
        assert collector.fetch_remote_data(db, data_length, x.keys()) == x

    @qc
    def write_data_locally(
        x=dict_(
            keys=str_(of='abc123-', min_length=36, max_length=36),
            values=list_(of=int_(min=0, max=3000), min_length=0, max_length=10),
            min_length=0, max_length=3
        )
    ):
        path = os.path.join(os.path.dirname(__file__), 'resources', 'vms', 'tmp')
        collector.write_data_locally(path, x)
        files = os.listdir(path)
        files.remove('.gitignore')
        assert set(files) == set(x.keys())

        for uuid, values in x.items():
            file = os.path.join(path, uuid)
            with open(file, 'r') as f:
                data = [int(x) for x in f.read().splitlines()]
                assert data == values
            os.remove(file)

    @qc(10)
    def get_cpu_time(
        uuid=str_(of='abc123-', min_length=36, max_length=36),
        x=int_(min=0)
    ):
        with MockTransaction:
            connection = libvirt.virConnect()
            domain = mock('domain')
            expect(connection).lookupByUUIDString(uuid). \
                and_return(domain).once()
            expect(domain).getCPUStats(True, 0). \
                and_return([{'cpu_time': x}]).once()
            assert collector.get_cpu_time(connection, uuid) == x

    @qc(10)
    def get_physical_cpus(x=int_(min=0, max=8)):
        with MockTransaction:
            connection = libvirt.virConnect()
            expect(connection).getInfo().and_return([0, 0, x]).once()
            assert collector.get_physical_cpus(connection) == x

    @qc
    def calculate_cpu_mhz(
        cpus=int_(min=1, max=8),
        time_period=int_(min=0, max=100),
        current_time=int_(min=100),
        cpu_time=int_(min=0, max=100),
        current_cpu_time=int_(min=100)
    ):
        previous_time = current_time - time_period
        previous_cpu_time = current_cpu_time - cpu_time
        assert collector. \
            calculate_cpu_mhz(cpus, previous_time, current_time,
                              previous_cpu_time, current_cpu_time) == \
            (cpu_time / (time_period * 1000000000 * cpus))
