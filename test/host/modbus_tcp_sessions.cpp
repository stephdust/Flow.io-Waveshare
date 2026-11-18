#include <assert.h>
#include "Modules/Network/ModbusTcpServerModule/ModbusTcpSessions.h"

int main() {
    using namespace ModbusTcpServer;
    TcpSessions sessions;
    for (uint8_t port = 0; port < kPortCount; ++port) {
        assert(sessions.accept(port) == int8_t(port * 2));
        assert(sessions.accept(port) == int8_t(port * 2 + 1));
        assert(sessions.accept(port) == -1);
        assert(sessions.active(port) == 2);
    }
    const uint8_t read24[] = {0x12,0x34,0,0,0,6,17,3,1,0xF4,0,24};
    size_t consumed = 0;
    assert(sessions.feed(0, read24, 4, consumed) == TcpSessions::FeedResult::Incomplete);
    assert(consumed == 4);
    assert(sessions.feed(0, read24 + 4, 8, consumed) == TcpSessions::FeedResult::Complete);
    assert(consumed == 8);
    ModbusTcpAdu::Request request{};
    assert(sessions.request(0, request));
    assert(request.address == 500 && request.count == 24);
    assert(sessions.feed(0, read24, sizeof(read24), consumed) == TcpSessions::FeedResult::Busy);
    sessions.clearRequest(0);
    const uint8_t combined[] = {0,1,0,0,0,6,17,3,3,0xE8,0,2,
                                0,2,0,0,0,6,17,3,1,0xF4,0,24};
    assert(sessions.feed(0, combined, sizeof(combined), consumed) == TcpSessions::FeedResult::Complete);
    assert(consumed == 12);
    assert(sessions.request(0, request) && request.address == 1000);
    sessions.clearRequest(0);
    size_t next = 0;
    assert(sessions.feed(0, combined + consumed, sizeof(combined) - consumed, next) ==
           TcpSessions::FeedResult::Complete);
    assert(sessions.request(0, request) && request.address == 500);
    sessions.release(0);
    assert(!sessions.occupied(0));
    assert(sessions.occupied(1));
    assert(sessions.active(0) == 1);
    assert(sessions.accept(0) == 0);
    const uint8_t bad[] = {0,1,0,1,0,6};
    assert(sessions.feed(0, bad, sizeof(bad), consumed) == TcpSessions::FeedResult::Invalid);
    const uint8_t unsupported[] = {0,3,0,0,0,2,17,1};
    assert(sessions.feed(0, unsupported, sizeof(unsupported), consumed) ==
           TcpSessions::FeedResult::Complete);
    assert(!sessions.request(0, request));
    assert(sessions.headerRequest(0, request));
    assert(request.transactionId == 3 && request.unitId == 17 && request.function == 1);
    sessions.release(0);
    sessions.release(1);
    assert(sessions.active(0) == 0);
    assert(sessions.active(1) == 2);
}
