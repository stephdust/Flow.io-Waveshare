#include <cassert>
#include <cstddef>
#include <cstdint>
#include "Modules/Network/ModbusIpServerModule/ModbusTcpFramer.h"
#include "Modules/Network/ModbusIpServerModule/ModbusMbapCodec.h"
using namespace flowio::modbus_ip;
int main(){
 const uint8_t pdu[]={3,0,0,0,1};
 uint8_t adu[32]{};
 const auto n=encodeAdu(adu,sizeof(adu),0x1234,4,pdu,sizeof(pdu));
 assert(n==12);
 TcpFramer f;std::size_t consumed=0;
 assert(f.push(adu,3,consumed)==TcpFramer::FeedResult::NeedMore&&consumed==3);
 assert(f.push(adu+3,n-3,consumed)==TcpFramer::FeedResult::Complete);
 assert(f.ready()&&f.size()==n);
 MbapHeader header{};const uint8_t* decoded=nullptr;std::size_t size=0;
 assert(decodeAdu(f.data(),f.size(),header,decoded,size));
 assert(header.transactionId==0x1234&&header.unitId==4&&size==5);
 f.reset();
 uint8_t joined[64]{};
 for(std::size_t i=0;i<n;++i){joined[i]=adu[i];joined[n+i]=adu[i];}
 assert(f.push(joined,2*n,consumed)==TcpFramer::FeedResult::Complete);
 assert(consumed==n);f.reset();
 assert(f.push(joined+consumed,n,consumed)==TcpFramer::FeedResult::Complete);
 f.reset();
 uint8_t invalid[12]{};
 for(std::size_t i=0;i<n;++i)invalid[i]=adu[i];
 invalid[2]=1;
 assert(f.push(invalid,n,consumed)==TcpFramer::FeedResult::Invalid);
 assert(!f.ready());
}
