#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sys

import paramiko
import logging
#email package start
import smtplib
from email.mime.text import MIMEText
#email package end
import time
import thread
import re
# ***************************************************
# Note master and slave node 						*
# must be able to access the Internet				*
# ***************************************************

#==========master==========
# 1.install pip
#	easy_install pip
# 2.install paramiko
# 	pip install paramiko==2.3.0

#==========slave==========
# 1.install wget
# 	sudo yum -y install wget qemu-kvm bonnie++ git bc
# 2.install iozone
#	wget http://ftp.tu-chemnitz.de/pub/linux/dag/redhat/el7/en/x86_64/rpmforge/RPMS/rpmforge-release-0.5.3-1.el7.rf.x86_64.rpm
#	sudo rpm -Uvh rpmforge-release*rpm
#	sudo yum install iozone
# 3.
#	wget http://dl.fedoraproject.org/pub/epel/7/x86_64/x/xmlstarlet-1.6.1-1.el7.x86_64.rpm
#	yum install libxslt
#	rpm -ivh xmlstarlet-1.6.1-1.el7.x86_64.rpm
# 4.
#	easy_install pip
#	sudo pip install nose==1.3.7

g_dependent_filename_list = [
								"ceph-10.2.9.tar.gz",
								"ceph-10.2.7.tar.gz",
								"ceph-test-10.2.7-0.el7.x86_64.rpm",
								"rbd-nbd-10.2.7-0.el7.x86_64.rpm",
								"rbd-fuse-10.2.7-0.el7.x86_64.rpm",
							]

g_available_scripts_rbd = [
							'verify_pool.sh',				# 结果在stdout中,标志一个OK
							'read-flags.sh',				# 结果在stdout中,标志一个OK
							'import_export.sh',				# 结果在stdout中,标志一个OK
							'copy.sh',						# 结果在stdout中,标志一个OK
							'test_lock_fence.sh',			# 结果在stdout中,标志一个OK
							'diff_continuous.sh',			# 结果在stdout中,标志一个OK
							'smalliobench.sh',				# 结果在stdout中,标志一个OK
							'permissions.sh',				# 结果在stdout中,标志一个OK
							'rbd-nbd.sh',					# 结果在stdout中,标志一个OK
							'kernel.sh',					# 结果在stdout中,标志一个OK
							'journal.sh',					# 结果在stdout中,标志一个OK，自动程序无log
							'test_librbd.sh',				# 结果在stdout中,标志 [  PASSED  ] 176 tests.
							'test_rbd_mirror.sh',			# 结果在stderr中,标志 [  PASSED  ] 42 tests.
							'test_librbd_api.sh',			# 结果在stdout中,标志 [  PASSED  ] 81 tests.
							'map-unmap.sh',					# 
							'huge-tickets.sh',				# 
							'test_rbdmap_RBDMAPFILE.sh',	# 
							'notify_master.sh',				# 与notify_slave.sh脚本一起执行
							'qemu-iotests.sh',				# 

							# 'test_admin_socket.sh',			# 
							# 'test_librbd_python.sh',		# 结果在stderr中，标志OK (SKIP=8) 或 	SKIP=8, errors=2, failures=4)
							# 'run_cli_tests.sh',				# 结果在stdout中,标志 No. of test cases passed:62 和 No. of test cases failed:13
						]

g_analytical_results_list_ok = [
						    'verify_pool.sh',
						    'read-flags.sh',
						    'import_export.sh',
						    'copy.sh',
						    'test_lock_fence.sh',
						    'journal.sh',
						    'diff_continuous.sh',
						    'smalliobench.sh',
						    'permissions.sh',
						    'rbd-nbd.sh',
						    'kernel.sh',
						    'test_librbd.sh',
							'test_rbd_mirror.sh',
							'test_librbd_api.sh',
							'map-unmap.sh',
							'huge-tickets.sh',
							'test_rbdmap_RBDMAPFILE.sh',
							'notify_master.sh',
							'notify_'
							'qemu-iotests.sh',
						]

g_analytical_results_list_special = [
							# 'run_cli_tests.sh',

						]

g_remote_host_ip = "192.168.0.11"	# ceph node IP address
g_remote_host_ssh_username = "root"	# ceph node ssh account
g_remote_host_ssh_password = "1234567890"	# ceph node ssh password

g_remote_host_rpm_storage_directory = "/tmp/"	# , The end must include "/"
g_ceph_tar_gz_name = "ceph-10.2.7.tar.gz"	# ceph source package
g_ceph_source_code_directory = "ceph-10.2.7"	# ceph source package after decompression directory name

g_current_path = os.path.dirname(os.path.abspath(__file__))	# The script executes the current directory
g_log_file = g_current_path + "/" + "exec_log" + "/" + "ceph_qa.log"	# Script execution log

# Initialize logger
def setup_logger(name, log_file, level=logging.DEBUG, format=False):
	handler = logging.FileHandler(log_file)
	if format is True:
		formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
		handler.setFormatter(formatter)
	logger = logging.getLogger(name)
	logger.setLevel(level)
	logger.addHandler(handler)
	return logger

g_logger = setup_logger("global log", g_log_file, level=logging.DEBUG, format=True)

# Copy files to remote machines
def remote_scp(remote_host_ip, remote_host_ssh_username, remote_host_ssh_password, local_path, remote_path):
	g_logger.debug("ceph_qa_remote_scp")
	t = paramiko.Transport((remote_host_ip,22))
	t.connect(username=remote_host_ssh_username, password=remote_host_ssh_password)
	sftp = paramiko.SFTPClient.from_transport(t)
	sftp.put(local_path,remote_path)
	t.close()

# Execute the command on the remote machine
def remote_command(remote_host_ip, remote_host_ssh_username, remote_host_ssh_password, remote_execution_cmd):
	g_logger.debug("ceph_qa_remote_command")
	g_logger.debug(remote_execution_cmd)
	ssh = paramiko.SSHClient()
	ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
	ssh.connect(remote_host_ip,username=remote_host_ssh_username,password=remote_host_ssh_password,allow_agent=False,look_for_keys=False)
	stdin, stdout, stderr = ssh.exec_command(remote_execution_cmd)
	stdout_tmp = stdout.readlines()
	stderr_tmp = stderr.readlines()
	ssh.close()
	return stdout_tmp, stderr_tmp

# Installation depends on the remote machine
def remote_install_dependent(remote_host_ip, remote_host_ssh_username, remote_host_ssh_password):
	g_logger.debug("ceph_qa_remote_install_dependent")
	remote_command(remote_host_ip,remote_host_ssh_username,remote_host_ssh_password,"sudo yum -y install wget qemu-kvm bonnie++")

# Delete all scripts to generate the pool in progress, prepare for the next test
def remote_exec_delete_all_test_pool():
	g_logger.debug("remote_exec_delete_all_test_pool")
	stdout, stderr = remote_command(g_remote_host_ip, g_remote_host_ssh_username, g_remote_host_ssh_password, "rados lspools")
	for poolname in stdout:
		poolname = poolname.strip()
		delete_pool_cmd = "ceph osd pool delete" + " " + poolname + " " + poolname + " " + "--yes-i-really-really-mean-it"
		remote_command(g_remote_host_ip, g_remote_host_ssh_username, g_remote_host_ssh_password, delete_pool_cmd)
		g_logger.debug(delete_pool_cmd)

# Create rbd pool
def remote_exec_create_rbd_pool():
	g_logger.debug("remote_exec_create_rbd_pool")
	stdout, stderr = remote_command(g_remote_host_ip, g_remote_host_ssh_username, g_remote_host_ssh_password, "ceph osd pool create rbd 512")

# The results are output to the file
def log_output_to_file(log_logger, result_file, result_content):
	result_logger = setup_logger(log_logger, result_file, level=logging.DEBUG)
	for p in result_content:
		result_logger.debug(p)

# Execute the notify_slave.sh script
def remote_exec_rbd_notify_slave_test(remote_host_ip,remote_host_ssh_username,remote_host_ssh_password,stdout_result_directory_name,stderr_result_directory_name):
	g_logger.debug("remote_exec_rbd_notify_slave_test")
	cmd = "sudo" + " " + g_remote_host_rpm_storage_directory + g_ceph_source_code_directory + "/qa/workunits/rbd/notify_slave.sh"
	stdout, stderr = remote_command(remote_host_ip, remote_host_ssh_username, remote_host_ssh_password, cmd)
	g_logger.debug(cmd)
	# stdout > file
	stdout_result_file = g_current_path + "/" + stdout_result_directory_name + "/" + "notify_slave.sh" + "_stdout" + ".log"
	log_output_to_file("stdout_notify_slave.sh", stdout_result_file, stdout)
	# stderr > file
	stderr_result_file = g_current_path + "/" + stderr_result_directory_name + "/" + "notify_slave.sh" + "_stderr" + ".log"
	log_output_to_file("stderr_notify_slave.sh", stderr_result_file, stderr)

# Compress log
def remote_compression_results(current_time, test_name, stdout_result_directory_name, stderr_result_directory_name):
	# tar -czf  2017-09-23_21-48-12_rbd_result.tar.gz 2017-09-23_21-48-12_rbd_stdout_result/ 2017-09-23_21-48-12_rbd_stderr_result/
	cmd = "tar -czf" + " " + current_time + "_" + test_name + "_result.tar.gz" + " " + stdout_result_directory_name + "/" + " " + stderr_result_directory_name + "/"
	os.system(cmd)
	g_logger.debug(cmd)


# analytical_results,
def analytical_results_ok(files, result_logger):
	for file in files:
		result = ""
		with open(file) as f:
			lines = f.readlines()
			for line in lines:
				pattern = re.compile(r'OK')
				match = pattern.match(line)
				if match:
					result = "PASSED"
		if result != "PASSED":
			result = "FAILED"
		result_logger.debug(result + "      " + file)
			
			# result_logger.debug("FAILED" + "      " + file)
# 
def analytical_results_special(files, result_logger):
	for file in files:
		result = ""
		with open(file) as f:
			lines = f.readlines()
			for line in lines:
				#(No. of test cases passed:.*)|(No. of test cases failed:.*)|
				pattern = re.compile(r'^(\[.*PASSED.*\].*)|^(\[.*FAILED.*\].*)|(OK.\(.*\))|(FAILED.*\(.*\))|(TEST: assert that rbdmap has not logged anything since TIMESTAMP)|(finished)|(.*iterations completed in.*seconds)|(creating.*keyring-baz)|(Passed all .*tests)|()')
				match = pattern.match(line)
				if match:
					result = match.group()
		result_logger.debug(match.group() + "      " + file)

def analytical_results_single_line(files, result_logger):
	for file in files:
		result = ""
		with open(file) as f:
			lines = f.readlines()
			for line in lines:
				pattern = re.compile(r'(^OK)|^(\[.*PASSED.*\].*)|^(\[.*FAILED.*\].*)|(OK.*\(.*\))|(FAILED.*\(.*\))|(TEST: assert that rbdmap has not logged anything since TIMESTAMP)|(finished)|(.*iterations completed in.*seconds)|(creating.*keyring-baz)|(Passed all .*tests)|()')
				match = pattern.match(line)
				if match:
					result = match.group()
		if result == "":
			result = "FAILED"
		result_logger.debug(file + "      " + result)

def analytical_results_multi_line(files, result_logger):
	for file in files:
		result = ""
		with open(file) as f:
			lines = f.readlines()
			for line in lines:
				pattern = re.compile(r'^(No. of test cases passed:.*)|^(No. of test cases failed:.*)')
				match = pattern.match(line)
				if match:
					result = result + "     " + match.group()
		result_logger.debug(file + "     " + result)


def analytical_results_to_file(files,):
	pass


# analytical_results, Composition absolute path
def composition_absolute_path(result_directory_name, analytical_results_list ,result_file_list):
	absolute_path = ""
	for f in analytical_results_list:
		absolute_path = os.path.join(result_directory_name + "/" + f + "_stdout.log")
		result_file_list.append(absolute_path)

def analytical_results(current_time, stdout_result_directory_name):
	file_list = []
	analytical_result_file = str(current_time) + "_rbd_analytical_result.log"
	result_logger = setup_logger("result log", analytical_result_file, level=logging.DEBUG)



	composition_absolute_path(stdout_result_directory_name, g_analytical_results_list_ok, file_list)


	analytical_results_single_line(file_list, result_logger)

	# Analyze the result of stdout for ok
	# composition_absolute_path(stdout_result_directory_name, g_analytical_results_list_ok, file_list)
	# analytical_results_ok(file_list, result_logger)
	# # 
	# del file_list[:]
	# composition_absolute_path(stdout_result_directory_name, g_analytical_results_list_special, file_list)
	# analytical_results_special(file_list, result_logger)
	# # 
	# del file_list[:]


# Execute the rbd script
def remote_exec_rbd_test(remote_host_ip, remote_host_ssh_username, remote_host_ssh_password):
	g_logger.debug("remote_exec_rbd_test")
	current_time = time.strftime("%Y-%m-%d_%H-%M-%S", time.localtime())
	stdout_result_directory_name = str(current_time) + "_rbd_stdout_result"
	stderr_result_directory_name = str(current_time) + "_rbd_stderr_result"
	os.mkdir(stdout_result_directory_name)
	os.mkdir(stderr_result_directory_name)
	for shell_name in g_available_scripts_rbd:
		remote_exec_delete_all_test_pool()
		remote_exec_create_rbd_pool()
		time.sleep(15)	# After the pool is created, the cluster will take some time to recover, otherwise the script will not get the results

		if shell_name == "notify_master.sh":
			thread.start_new_thread(remote_exec_rbd_notify_slave_test,(remote_host_ip,remote_host_ssh_username,remote_host_ssh_password,stdout_result_directory_name,stderr_result_directory_name))
		cmd = "sudo" + " " + g_remote_host_rpm_storage_directory + g_ceph_source_code_directory + "/qa/workunits/rbd/" + str(shell_name)
		stdout, stderr = remote_command(remote_host_ip, remote_host_ssh_username, remote_host_ssh_password, cmd)
		g_logger.debug(cmd)

		# stdout > file
		stdout_result_file = g_current_path + "/" + stdout_result_directory_name + "/" + shell_name + "_stdout" + ".log"
		log_output_to_file("stdout_" + str(shell_name), stdout_result_file, stdout)
		
		# stderr > file
		stderr_result_file = g_current_path + "/" + stderr_result_directory_name + "/" + shell_name + "_stderr" + ".log"
		log_output_to_file("stderr_" + str(shell_name), stderr_result_file, stderr)

	remote_compression_results(current_time, "rbd", stdout_result_directory_name, stderr_result_directory_name)
	# analytical_results(current_time, stdout_result_directory_name)

if __name__=="__main__":
	# 1.copy rpm to remote host
	for f in g_dependent_filename_list:
		local_ceph_source_code_path = os.path.dirname(os.path.abspath(__file__)) + "/ceph_source_code/" + f
		remote_ceph_soutce_code_path = g_remote_host_rpm_storage_directory + f
		remote_scp(g_remote_host_ip, g_remote_host_ssh_username, g_remote_host_ssh_password, local_ceph_source_code_path, remote_ceph_soutce_code_path)

	# 2.unzip ceph-10.2.7.tar.gz, Force the rpm package to be installed
	local_ceph_source_code_path = os.path.dirname(os.path.abspath(__file__)) + "/ceph_source_code/" + g_ceph_tar_gz_name
	remote_ceph_soutce_code_path = g_remote_host_rpm_storage_directory + g_ceph_tar_gz_name

	unzip_ceph_package_cmd = "tar" + " " + "zxvf" + " " + g_remote_host_rpm_storage_directory + g_ceph_tar_gz_name + " " + "-C" + " " + g_remote_host_rpm_storage_directory
	remote_command(g_remote_host_ip, g_remote_host_ssh_username, g_remote_host_ssh_password, unzip_ceph_package_cmd)

	install_the_rpm_package_cmd = "rpm" + " " + "-Uivh" + " " + g_remote_host_rpm_storage_directory + "*.rpm" + " " + "--nodeps --force"
	remote_command(g_remote_host_ip, g_remote_host_ssh_username, g_remote_host_ssh_password, install_the_rpm_package_cmd)

	# 3.Start testing rbd
	remote_exec_rbd_test(g_remote_host_ip, g_remote_host_ssh_username, g_remote_host_ssh_password)
