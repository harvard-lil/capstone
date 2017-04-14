# -*- mode: ruby -*-
# vi: set ft=ruby :

# Salt Minion ID not available until v1.8.1
Vagrant.require_version ">= 1.8.1"
VAGRANTFILE_API_VERSION = "2"

ENV["LC_ALL"] = "en_US.UTF-8"

if ENV['VAGRANT_DEBUG']
  #require 'pry-byebug'
  #binding.pry
end

Vagrant.configure(VAGRANTFILE_API_VERSION) do |config|

  config.vm.box_check_update = true
  config.vm.define :node do |node|
    node.vm.box = "debian/jessie64"
    # We do not generate a random hostname and assign it here
    # as the vagrant instance will change its hostname every
    # time it is booted
    # HOSTNAME = [*('A'..'Z')].sample(8).join
    # node.vm.hostname = "#{HOSTNAME}.dev.local"

    # node.vm.network :forwarded_port, guest: 8000, host: 8000 # django dev server
    # node.vm.network :forwarded_port, guest: 9000, host: 9000 # nginx server (not started by default)

    node.vm.network :private_network, type: :dhcp
    node.vm.synced_folder ".", "/vagrant", :nfs => true, :mount_options => ['actimeo=1']
    # configure CPU/RAM
    # https://stefanwrobel.com/how-to-make-vagrant-performance-not-suck
    host = RbConfig::CONFIG['host_os']
    # Give VM 1/4 system memory & access to all cpu cores on the host
    if host =~ /darwin/
      cpus = `sysctl -n hw.ncpu`.to_i
      # sysctl returns Bytes and we need to convert to MB
      mem = `sysctl -n hw.memsize`.to_i / 1024 / 1024 / 4
    elsif host =~ /linux/
      cpus = `nproc`.to_i
      # meminfo shows KB and we need to convert to MB
      mem = `grep 'MemTotal' /proc/meminfo | sed -e 's/MemTotal://' -e 's/ kB//'`.to_i / 1024 / 4
    else 
      cpus = 2
      mem = 1024
    end

    if ARGV[0] == "up"
      puts("Using #{mem}MB RAM and #{cpus} CPUs.") 
    end
 
    node.vm.provider "virtualbox" do |vb|
      if ENV['VAGRANT_DEBUG']
        vb.gui = true
      else 
        vb.gui = false
      end
      vb.memory = mem
      vb.cpus = cpus
      # if ENV['VAGRANT_NFS']
      #   # configure NFS mount for speed
      #   node.vm.network :private_network, type: :dhcp
      #   node.vm.synced_folder ".", "/vagrant", type: "nfs",
      #   mount_options: ['actimeo=1']  # check each second for django reload
      # end
    end

    node.vm.provider "vmware_fusion" do |vf, override|
      if ENV['VAGRANT_DEBUG']
        vf.gui = true
      else 
        vf.gui = false
      end
      #override.vm.box = "meangrape/perma_dev_vmware"
      vf.vmx["memsize"] = mem
      vf.vmx["numvcpus"] = cpus
    end

    # Set and fix random hostname and permissions
    node.vm.provision "shell", inline: <<-EOF
      ## install salt-minion per https://repo.saltstack.com/#debian
      wget -O - https://repo.saltstack.com/apt/debian/8/amd64/latest/SALTSTACK-GPG-KEY.pub | sudo apt-key add -
      echo 'deb http://repo.saltstack.com/apt/debian/8/amd64/latest jessie main' >> /etc/apt/sources.list.d/saltstack.list
      apt-get update
      aptitude install salt-minion -y
      aptitude install python-git -y

      # Following line is for debugging; too difficult to pass ruby ENV settings
      # to a shell script. Also very good for educational purposes if you don't
      # use the shell a lot
      # set -vx

      # Generate a hostname with eight lower-case alphanumeric characters
      my_hostname=$( tr -dc 'a-z0-9' < /dev/urandom | fold -w8  | head -1 )

      # Check to see if /etc/hostname contains "jessie" (was "debian")
      $( diff -qs /etc/hostname <( echo 'jessie' ) 2>&1>/dev/null )
      
      # If so, then change the hostname & related files
      if [[ $? -eq 0 ]] 
      then
        hostnamectl set-hostname $my_hostname 2>&1>/dev/null

        # Remove blanks and comments from /etc/hosts
        sed -i -e 's/#.*$//' -e '/^$/d' /etc/hosts

        # Prepend our hostname in /etc/hosts; remove original box hostname
        sed -i '/debian.local/d' /etc/hosts
        sed -i "1i 127.0.0.1       $my_hostname.capstone.local       $my_hostname"       /etc/hosts 

        # Overwrite mailname
        echo "$my_hostname.capstone.local" > /etc/mailname
      fi 

      my_minion_id=$(< /etc/salt/minion_id )
      if [[ "$my_minion_id" == 'jessie.raw' ]]
      then
        hostname -f > /etc/salt/minion_id
        rm -rf /etc/salt/pki/*
      fi

      # update the salt master and restart the minion
      sed -i 's/^#master: salt/master: saltmaster.lil.tools/' /etc/salt/minion
      /etc/init.d/salt-minion restart

      # I've seen vagrant put down /etc/salt/minion as vagrant:vagrant
      chown -R root:root /etc/salt
    EOF

    ## set timezone to UTC
    node.vm.provision :shell, :inline => "echo 'Etc/UTC' | sudo tee /etc/timezone && dpkg-reconfigure --frontend noninteractive tzdata"

    ## Saltstack configuration
    # node.vm.provision :salt do |salt|
    #   if ENV['VAGRANT_DEBUG']
    #     salt.verbose = true
    #   end
    #   salt.minion_config = "/etc/salt/minion"
    #   salt.run_highstate = true
    # end
  end
end
