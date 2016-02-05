p_flag="true"

a=$(networksetup -getairportnetwork en0 | sed -e "s/Current Wi-Fi Network: //")
echo ${a}

if [ $a = "p_wifi" ] || [ $a = "p_wifi2" ]; then
	echo "p_on"
	proxy1=proxy.jp
	port1=36436
else
	echo "おうちいんたーねっと"
	proxy1=""
	port1=0
	p_flag="false"
fi

pp=$proxy1$port1
export http_proxy=$pp
export https_proxy=$http_proxy
export all_proxy=$http_proxy

if [ $p_flag = "true" ]; then
	echo "p _ on"
	sudo networksetup -setwebproxy Wi-Fi $proxy1 $port1
	sudo networksetup -setwebproxystate Wi-Fi on
	sudo networksetup -setftpproxy Wi-Fi $proxy1 $port1
	sudo networksetup -setftpproxystate Wi-Fi on	
	sudo networksetup -setsecurewebproxy Wi-Fi $proxy1 $port1
	sudo networksetup -setsecurewebproxystate Wi-Fi on
	sudo networksetup -setstreamingproxy Wi-Fi $proxy1 $port1
	sudo networksetup -setstreamingproxystate Wi-Fi on
	sudo networksetup -setgopherproxy Wi-Fi $proxy1 $port1
	sudo networksetup -setgopherproxystate Wi-Fi on
	sudo networksetup -setsocksfirewallproxy Wi-Fi $proxy1 $port1
	sudo networksetup -setsocksfirewallproxystate Wi-Fi on
else
	echo "p _ off"
	sudo networksetup -setwebproxystate Wi-Fi off
	sudo networksetup -setwebproxystate Wi-Fi off
	sudo networksetup -setftpproxystate Wi-Fi off	
	sudo networksetup -setsecurewebproxystate Wi-Fi off
	sudo networksetup -setstreamingproxystate Wi-Fi off
	sudo networksetup -setgopherproxystate Wi-Fi off
	sudo networksetup -setsocksfirewallproxystate Wi-Fi off
fi

echo "now_status"
b=$(networksetup -getwebproxy Wi-Fi)
echo ${b}
echo ${!b[*]}