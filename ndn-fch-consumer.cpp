// correct way to include ndn-cxx headers
// #include <ndn-cxx/face.hpp>
#include "face.hpp"
#include "encoding/block-helpers.hpp"
#include <stdlib.h>
#include <stdio.h>
#include <curl/curl.h>
#include <string>
#include <iostream>

namespace ndn {
namespace ndnfch {
size_t writeFunction(void* ptr, size_t size, size_t nmemb, std::string* data)
{
    data->append((char*)ptr, size * nmemb);
    return size * nmemb;
}

class Consumer : noncopyable {
public:
    void
    run()
    {
        CURL* curl = curl_easy_init();
        if (curl) {
            curl_easy_setopt(curl, CURLOPT_URL, "http://icanhazip.com");
            curl_easy_setopt(curl, CURLOPT_USERAGENT, "curl/7.42.0");
            curl_easy_setopt(curl, CURLOPT_TCP_KEEPALIVE, 0L);

            std::string response_string;
            curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, writeFunction);
            curl_easy_setopt(curl, CURLOPT_WRITEDATA, &response_string);

            curl_easy_perform(curl);
            curl_easy_cleanup(curl);
            curl = NULL;

            std::cout << "IP address: " + response_string << "\n";

            std::string fchprefix = "/ndn/edu/ucla/cs/gszliu/ndn-fch/";
            std::string fchinterest = fchprefix + response_string;

            std::cout << "Preparing Interest: " + fchinterest << "\n";

            Interest interest(Name(fchinterest.c_str()));
            interest.setInterestLifetime(time::milliseconds(5000));
            interest.setMustBeFresh(true);

            m_face.expressInterest(interest,
                bind(&Consumer::onData, this, _1, _2),
                bind(&Consumer::onTimeout, this, _1));

            std::cout << "Sending " << interest << std::endl;

            // processEvents will block until the requested data received or timeout occurs
            m_face.processEvents();
        }
    }

private:
    void
    onData(const Interest& interest, const Data& data)
    {
    	std::string hub = readString(data.getContent());
    	std::cout << "\nResponse received!" << std::endl;
        std::cout << "Closest hub: " << hub << std::endl;
        //std::cout << "Connecting to hub..." << std::endl;

        std::string register_all = "sudo nfdc register / udp4://"	 + hub;
        std::string register_localhop = "sudo nfdc register /localhop/nfd udp4://" + hub;

        //std::system(register_all.c_str());
        //std::system(register_localhop.c_str());

        std::cout << "Execute commands:" << std::endl;
        std::cout << "\t" << register_all << std::endl;
        std::cout << "\t" << register_localhop << std::endl;
    }

    void
    onTimeout(const Interest& interest)
    {
        std::cout << "Timeout " << interest << std::endl;
    }

private:
    Face m_face;
};
}}

int main(int argc, char** argv)
{
    ndn::ndnfch::Consumer consumer;
    try {
        consumer.run();
    }
    catch (const std::exception& e) {
        std::cerr << "ERROR: " << e.what() << std::endl;
    }
    return 0;
}
