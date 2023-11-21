#!/bin/bash
sudo yum upgrade -y
sudo yum install -y httpd 
sudo chkconfig httpd on
sudo servce httpd enable 
sudo service httpd start
