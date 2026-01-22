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
int test_flags;
serial::Serial *com_port_;
uint8_t hand_state_;

bool 
set_6short(serial::Serial *port, int add, std::vector<int> values)
{
    int EXID_CAN = 0x04000000 + (add << 14) + 0x3FFF;

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
    output.push_back((unsigned int)values[0] & 0xFF); // -- 6
    output.push_back(((unsigned int)values[0] >> 8) & 0xFF); // -- 7
    output.push_back((unsigned int)values[1] & 0xFF); // -- 8
    output.push_back(((unsigned int)values[1] >> 8) & 0xFF); // -- 9
    output.push_back((unsigned int)values[2] & 0xFF); // -- 10
    output.push_back(((unsigned int)values[2] >> 8) & 0xFF); // -- 11
    output.push_back((unsigned int)values[3] & 0xFF); // -- 12
    output.push_back(((unsigned int)values[3] >> 8) & 0xFF); // -- 13
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
    if (test_flags == 1)
        ROS_INFO_STREAM("Write: " << s1);

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
    if (test_flags == 1)
        ROS_INFO_STREAM("Read: " << s2);



    EXID_CAN = 0x04000000 + ((add + 8) << 14) + 0x3FFF;

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
    output.push_back((unsigned int)values[4] & 0xFF); // -- 6
    output.push_back(((unsigned int)values[4] >> 8) & 0xFF); // -- 7
    output.push_back((unsigned int)values[5] & 0xFF); // -- 8
    output.push_back(((unsigned int)values[5] >> 8) & 0xFF); // -- 9
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
    if (test_flags == 1)
        ROS_INFO_STREAM("Write: " << s1);

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
    if (test_flags == 1)
        ROS_INFO_STREAM("Read: " << s2);

    if (input.size() > 0)
        return true;
    else
        return false;
}


void setANGLE1(serial::Serial *port, int angle0, int angle1, int angle2, 
int angle3, int angle4, int angle5) 		
{
    int add = 1486;
    int val_array[6] = {angle0, angle1, angle2, 
    angle3, angle4, angle5};
    std::vector<int> values(val_array, val_array + 6);
    set_6short(port, add, values);
}
int Arr[12];

void arrayCallback1(const std_msgs::Int32MultiArray::ConstPtr& array)
{

    int i = 0;
    // print all the remaining numbers
    for(std::vector<int>::const_iterator it = array->data.begin(); it != array->data.end(); ++it)
    {

        Arr[i] = *it;
        printf("%d, ", Arr[i]);
        i++;
    }
    setANGLE1(com_port_,Arr[0],Arr[1],Arr[2],Arr[3],Arr[4],Arr[5]);

    return;
}
int main(int argc, char *argv[])
{
    ros::init(argc, argv, "handcontroltopicpublisher1");
    ros::NodeHandle nh;

    //topic
    ros::Subscriber sub = nh.subscribe("chatter1", 1000, arrayCallback1);

    ros::Rate loop_rate(10);

    //Read launch file params
    nh.getParam("inspire_hand/hand_id", hand_id_);
    nh.getParam("inspire_hand/portname", port_name_);
    nh.getParam("inspire_hand/baudrate", baudrate_);
    nh.getParam("inspire_hand/test_flags", test_flags);
    //Initialize and open serial port
    com_port_ = new serial::Serial(port_name_, (uint32_t)baudrate_, serial::Timeout::simpleTimeout(100));

    ros::spin();

    return(EXIT_SUCCESS);
}
