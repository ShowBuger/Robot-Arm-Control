#include <iostream>
#include <sstream>
#include <string>
#include <vector>
#include <boost/asio.hpp>
#include <iomanip>

using namespace std;
using namespace boost::asio;

// 寄存器字典
const struct {
    const char* name;
    int address;
} regdict[] = {
    {"angleSet", 1486},
    {"forceSet", 1498},
    {"speedSet", 1522},  
    {"angleAct", 1546},
    {"forceAct", 1582}
};

class SerialPort {
public:
    SerialPort(const string& port, unsigned int baudrate) : io(), serial(io, port) {
        serial.set_option(serial_port_base::baud_rate(baudrate));
        cout << "串口 " << port << " 已打开" << endl;
    }

    void write(const vector<unsigned char>& data) {
        boost::asio::write(serial, buffer(data));
    }

    vector<unsigned char> read(size_t length) {
        vector<unsigned char> buffer(length);
        boost::asio::read(serial, boost::asio::buffer(buffer.data(), length));
        return buffer;  
    }

private:
    io_context io;
    serial_port serial;
};

// 根据寄存器名称获取地址
int getAddressByName(const string& reg_name) {
    for (const auto& reg : regdict) {
        if (reg.name == reg_name) {
            return reg.address;  // 返回匹配的地址
        }
    }
    return -1;  // 未找到寄存器名称，返回 -1
}

void write_register(SerialPort& serial, int address_decimal, const string& id_value, const vector<int>& values_to_write) {
    // 发送请求数据
    vector<unsigned char> send_buffer;
    send_buffer.push_back(0xEB); 
    send_buffer.push_back(0x90);
    send_buffer.push_back(static_cast<unsigned char>(stoi(id_value)));  
    size_t num_values = values_to_write.size();
    unsigned char data_length = static_cast<unsigned char>(num_values * 2 + 3); 
    send_buffer.push_back(data_length);  
    send_buffer.push_back(0x12); 
    send_buffer.push_back(static_cast<unsigned char>(address_decimal & 0xFF));  // 地址低八位
    send_buffer.push_back(static_cast<unsigned char>((address_decimal >> 8) & 0xFF));  // 地址高八位

    for (int value : values_to_write) {
        send_buffer.push_back(static_cast<unsigned char>(value & 0xFF)); 
        send_buffer.push_back(static_cast<unsigned char>((value >> 8) & 0xFF));  
    }

    unsigned char checksum = 0;
    for (size_t k = 2; k < send_buffer.size(); ++k) {
        checksum += send_buffer[k];
    }

    send_buffer.push_back(checksum & 0xFF);  // 添加校验和

    cout << "发送的写入数据: ";
    for (auto byte : send_buffer) {
        cout << hex << setw(2) << setfill('0') << (int)byte << " ";
    }
    cout << endl;

    serial.write(send_buffer);  
}



// 读取寄存器的函数
void read_register(SerialPort& serial, int address_decimal, const string& id_value, size_t length_to_read) {
    vector<int> parsed_values;

    // 发送请求数据
    vector<unsigned char> send_buffer;
    send_buffer.push_back(0xEB); 
    send_buffer.push_back(0x90);
    send_buffer.push_back(static_cast<unsigned char>(stoi(id_value)));  
    send_buffer.push_back(0x04);
    send_buffer.push_back(0x11);
    send_buffer.push_back(static_cast<unsigned char>(address_decimal & 0xFF));  // 地址低八位
    send_buffer.push_back(static_cast<unsigned char>((address_decimal >> 8) & 0xFF));  // 地址高八位
    send_buffer.push_back(0x0C); 

    unsigned char checksum = 0;
    for (size_t k = 2; k < send_buffer.size(); ++k) {
        checksum += send_buffer[k];
    }

    send_buffer.push_back(checksum & 0xFF);

    cout << "发送的完整数据: ";
    for (auto byte : send_buffer) {
        cout << hex << setw(2) << setfill('0') << (int)byte << " ";
    }
    cout << endl;
    serial.write(send_buffer);  

    // 读取响应数据
    vector<unsigned char> received_data = serial.read(length_to_read);

    // 打印原始响应数据
    cout << "接收到的原始响应数据: ";
    for (auto byte : received_data) {
        cout << hex << setw(2) << setfill('0') << (int)byte << " ";
    }
    cout << endl;

    // 解析响应
    for (size_t j = 7; j < 19; j += 2) {  // 假设数据从第7字节开始到第19字节
        if (j + 1 < received_data.size()) {
            int value = (received_data[j + 1] << 8) | received_data[j];
            if (value > 6000) {
                value = 0;
            }
            parsed_values.push_back(value);
        }
    }

    cout << "参数： ";
    for (int value : parsed_values) {
        cout << dec << value << " ";  
    }
    cout << endl; 
}

int main() {
    string port = "/dev/ttyUSB0";  // 根据实际情况修改串口名
    SerialPort serial(port, 115200);

    // 读取寄存器名称输入
    cout << "请输入要操作的字典名（如 set angleSet 或 get angleSet）: ";
    string input;
    getline(cin, input);  

    stringstream ss(input);
    string operation, reg_name;
    ss >> operation >> reg_name;  

    // 根据寄存器名称获取地址
    int address_decimal = getAddressByName(reg_name);
    if (address_decimal == -1) {
        cout << "未找到对应的寄存器: " << reg_name << endl;
        return 1;  // 如果未找到寄存器，提前退出
    }

    cout << "请输入ID值: ";
    string id_value;
    cin >> id_value;  // 读取ID

    if (operation == "set") {  // 写入操作
        cout << "请输入要写入的值（用空格分隔）：";
        vector<int> values_to_write;
        int value;
        while (cin >> value) {
            values_to_write.push_back(value);  
            if (cin.peek() == '\n') break;      
        }

        cout << "写入寄存器: " << reg_name << " 地址: " << address_decimal << " 值数量: " << values_to_write.size() << endl;
        write_register(serial, address_decimal, id_value, values_to_write);
    } else if (operation == "get") {  
        cout << "读取寄存器: " << reg_name << " 地址: " << address_decimal << endl;
        read_register(serial, address_decimal, id_value, 20); 
    } else {
        cout << "无效的操作类型！" << endl;
    }

    return 0;
}
