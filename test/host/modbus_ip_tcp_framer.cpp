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
 // A malformed header must not poison the next request.
 assert(f.push(adu,n,consumed)==TcpFramer::FeedResult::Complete);
 f.reset();
 uint8_t invalidLength[12]{};
 for(std::size_t i=0;i<n;++i)invalidLength[i]=adu[i];
 invalidLength[4]=0;invalidLength[5]=1;
 assert(f.push(invalidLength,n,consumed)==TcpFramer::FeedResult::Invalid);
 assert(!f.ready());
 invalidLength[4]=1;invalidLength[5]=0;
 assert(f.push(invalidLength,n,consumed)==TcpFramer::FeedResult::Invalid);
 assert(!f.ready());
 assert(f.push(adu,n,consumed)==TcpFramer::FeedResult::Complete);
 // MBAP decoder must reject inconsistent lengths and unsupported protocols.
 MbapHeader badHeader{};const uint8_t* badPdu=nullptr;std::size_t badSize=0;
 uint8_t wrongLength[32]{};
 for(std::size_t i=0;i<n;++i)wrongLength[i]=adu[i];
 wrongLength[5]=5;
 assert(!decodeAdu(wrongLength,n,badHeader,badPdu,badSize));
 wrongLength[5]=6;wrongLength[3]=1;
 assert(!decodeAdu(wrongLength,n,badHeader,badPdu,badSize));
 assert(!decodeAdu(adu,7,badHeader,badPdu,badSize));
 assert(!decodeAdu(adu,n-1,badHeader,badPdu,badSize));
}

