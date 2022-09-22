# -*-ruby-*-
Vagrant.configure("2") do |config|
    # From https://app.vagrantup.com/metaswitch-its/boxes/centos7-min-xfce
    # config.vm.box = "metaswitch-its/centos7-min-xfce"
    config.vm.box = "centos/7"
    config.vm.hostname = "test-ansible-box"
    config.vm.network "private_network", ip: "10.10.10.10"
    config.vm.provider "virtualbox" do |v|
        v.memory = 4096
        v.cpus = 2
        # Display the VirtualBox GUI when booting the machine
        # v.gui = true
    end
end
