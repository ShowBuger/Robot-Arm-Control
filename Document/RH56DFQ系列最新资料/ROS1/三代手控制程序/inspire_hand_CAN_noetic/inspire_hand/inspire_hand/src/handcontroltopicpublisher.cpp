#include <ros/ros.h>
#include <hand_control.h>
#include <stdio.h>
#include <stdlib.h>
#include <vector>
#include <iostream>
#include <std_msgs/String.h>
#include "std_msgs/MultiArrayLayout.h"
#include "std_msgs/MultiArrayDimension.h"
#include "std_msgs/Int32MultiArray.h"

using namespace std;

int hand_id_;
std::string port_name_;
int baudrate_;
int test_flags_;
int Serial_flags_;
serial::Serial *com_port_;
int hand_state_;
float curangle_[6];
float curforce_[6];

std::vector<int> 
get_6short(serial::Serial *port, int add)
{
    std::vector<int> returnval;

    int EXID_CAN = 0x00000000 + (add << 14) + 0x3FFF;

    std::vector<uint8_t> output;
    // frame head
    output.push_back(0xAA);
    output.push_back(0xAA);
    // identifier
    output.push_back((EXID_CAN >> 0) & 0xFF);
    output.push_back((EXID_CAN >> 8) & 0xFF);
    output.push_back((EXID_CAN >> 16) & 0xFF);
    output.push_back((EXID_CAN >> 24) & 0xFF);
    // content
    output.push_back(0x08); // -- 6
    output.push_back(0x0); // -- 7
    output.push_back(0x0); // -- 8
    output.push_back(0x0); // -- 9
    output.push_back(0x0); // -- 10
    output.push_back(0x0); // -- 11
    output.push_back(0x0); // -- 12
    output.push_back(0x0); // -- 13
    // length
    output.push_back(0x08);
    // extension
    output.push_back(0x00);
    output.push_back(0x01);
    output.push_back(0x00);
    // checknum
    uint8_t check_num = 0;
    for(int byte = 2; byte < 18; byte++)
    {
        check_num += output[byte];
    }
    output.push_back(check_num);
    // frame tail
    output.push_back(0x55);
    output.push_back(0x55);
    // adding 0xA5 before special hexnumbers
    int tx_len = 21;
    int i = 2;
    while(true)
    {
        if(output[i] == 0xAA || output[i] == 0x55 || output[i] == 0xA5)
        {
            tx_len++;
            output.push_back(0x0); // placeholder
            for(int j = tx_len; j > i; j--)
            {
                output[j] = output[j - 1];
            }
            output[i] = 0xA5;
            i++;
        }
        i++;
        if(i == tx_len - 2)
        {
            break;
        }
    }
    
    //Send message to the module
    port->write(output);

    ros::Duration(0.015).sleep();

    std::string s1;
    for (int i = 0; i < output.size(); ++i)
    {
        char str[16];
        sprintf(str, "%02X", output[i]);
        s1 = s1 + str + " ";
    }
    if (test_flags_ == 1)
        ROS_INFO_STREAM("Write: " << s1);

    //Read response
    std::vector<uint8_t> input;
    while (input.empty())
    {
        port->read(input, (size_t)64);
    }

    std::string s2;
    for (int i = 0; i < input.size(); ++i)
    {
        char str[16];
        sprintf(str, "%02X", input[i]);
        s2 = s2 + str + " ";
    }
    if (test_flags_ == 1)
        ROS_INFO_STREAM("Read: " << s2);

    for (int j = 0; j < 4; j++)
        returnval.push_back(((input[7 + j * 2] << 8) & 0xff00) + input[6 + j * 2]);



    EXID_CAN = 0x00000000 + ((add + 8) << 14) + 0x3FFF;

    output.clear();
    // frame head
    output.push_back(0xAA);
    output.push_back(0xAA);
    // identifier
    output.push_back((EXID_CAN >> 0) & 0xFF);
    output.push_back((EXID_CAN >> 8) & 0xFF);
    output.push_back((EXID_CAN >> 16) & 0xFF);
    output.push_back((EXID_CAN >> 24) & 0xFF);
    // content
    output.push_back(0x04); // -- 6
    output.push_back(0x0); // -- 7
    output.push_back(0x0); // -- 8
    output.push_back(0x0); // -- 9
    output.push_back(0x0); // -- 10
    output.push_back(0x0); // -- 11
    output.push_back(0x0); // -- 12
    output.push_back(0x0); // -- 13
    // length
    output.push_back(0x04);
    // extension
    output.push_back(0x00);
    output.push_back(0x01);
    output.push_back(0x00);
    // checknum
    check_num = 0;
    for(int byte = 2; byte < 18; byte++)
    {
        check_num += output[byte];
    }
    output.push_back(check_num);
    // frame tail
    output.push_back(0x55);
    output.push_back(0x55);
    // adding 0xA5 before special hexnumbers
    tx_len = 21;
    i = 2;
    while(true)
    {
        if(output[i] == 0xAA || output[i] == 0x55 || output[i] == 0xA5)
        {
            tx_len++;
            output.push_back(0x0); // placeholder
            for(int j = tx_len; j > i; j--)
            {
                output[j] = output[j - 1];
            }
            output[i] = 0xA5;
            i++;
        }
        i++;
        if(i == tx_len - 2)
        {
            break;
        }
    }
    
    //Send message to the module
    port->write(output);

    ros::Duration(0.015).sleep();

    s1 = "";
    for (int i = 0; i < output.size(); ++i)
    {
        char str[16];
        sprintf(str, "%02X", output[i]);
        s1 = s1 + str + " ";
    }
    if (test_flags_ == 1)
        ROS_INFO_STREAM("Write: " << s1);

    //Read response
    input.clear();
    while (input.empty())
    {
        port->read(input, (size_t)64);
    }

    s2 = "";
    for (int i = 0; i < input.size(); ++i)
    {
        char str[16];
        sprintf(str, "%02X", input[i]);
        s2 = s2 + str + " ";
    }
    if (test_flags_ == 1)
        ROS_INFO_STREAM("Read: " << s2);

    for (int j = 4; j < 6; j++)
        returnval.push_back(((input[7 + (j - 4) * 2] << 8) & 0xff00) + input[6 + (j - 4) * 2]);

    return returnval;
}

void getANGLE_ACT1(serial::Serial *port)
{
    int add = 1546;
    std::vector<int> values(get_6short(port, add));

    curangle_[0] = float(values[0]);
    curangle_[1] = float(values[1]);
    curangle_[2] = float(values[2]);
    curangle_[3] = float(values[3]);
    curangle_[4] = float(values[4]);
    curangle_[5] = float(values[5]);
}

void getFORCE_ACT1(serial::Serial *port)
{
    int add = 1582;
    std::vector<int> values(get_6short(port, add));

    curforce_[0] = float(values[0]);
    curforce_[1] = float(values[1]);
    curforce_[2] = float(values[2]);
    curforce_[3] = float(values[3]);
    curforce_[4] = float(values[4]);
    curforce_[5] = float(values[5]);
}

int main(int argc, char *argv[])
{
    ros::init(argc, argv, "handcontroltopicpublisher");
    ros::NodeHandle nh;

    //topic
    ros::Publisher chatter_pub = nh.advertise<std_msgs::Int32MultiArray>("chatter", 1000);

    ros::Rate loop_rate(10);

    //Read launch file params
    nh.getParam("inspire_hand/hand_id", hand_id_);
    nh.getParam("inspire_hand/portname", port_name_);
    nh.getParam("inspire_hand/baudrate", baudrate_);
    nh.getParam("inspire_hand/test_flags", test_flags_);
    
    //Initialize and open serial port
    com_port_ = new serial::Serial(port_name_, (uint32_t)baudrate_, serial::Timeout::simpleTimeout(100));

    while (ros::ok())
    {
        //get the param Serial_flags
        nh.getParam("inspire_hand/Serial_flags", Serial_flags_);
        if(Serial_flags_ == 0)
        {
            ROS_INFO_STREAM("close the Serial");
        }
        else if (Serial_flags_ == 1)
        {
            std_msgs::Int32MultiArray array;

            //Clear array
            array.data.clear();
            getANGLE_ACT1(com_port_);
            getFORCE_ACT1(com_port_);

            for (int i = 0; i < 6; i++)
            {
                //assign array a random number between 0 and 255.
                array.data.push_back(curangle_[i]);
            }
            for (int i = 0; i < 6; i++)
            {
                //assign array a random number between 0 and 255.
                array.data.push_back(curforce_[i]);
            }
            //Publish array
            chatter_pub.publish(array);
            loop_rate.sleep();
        }
    }

    return (EXIT_SUCCESS);
}
