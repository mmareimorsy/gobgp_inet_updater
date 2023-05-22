# Possible BGP Path Attributes
# ORIGIN - supported	
# AS_PATH - supported	
# NEXT_HOP - always set to gobgp local neighbor address	
# MULTI_EXIT_DISC - supported	
# LOCAL_PREF - skipped, most likely eBGP sessions so no point	
# ATOMIC_AGGREGATE - 
# AGGREGATOR	
# COMMUNITY	- supported
# ORIGINATOR_ID	
# CLUSTER_LIST	
# MP_REACH_NLRI	
# MP_UNREACH_NLRI	
# EXTENDED COMMUNITIES - skipped currently 	
# AS4_PATH	
# AS4_AGGREGATOR	
# AIGP	
# LARGE_COMMUNITY - supported	
# ATTR_SET	

import grpc
from google.protobuf.any_pb2 import Any

import gobgp_pb2
import gobgp_pb2_grpc
import attribute_pb2
import ipaddress

# 100 msecs timeout for update
_TIMEOUT_SECONDS = 100/1000

# return the subnet & the prefix length
def get_pfx_len(pfx):
    return pfx.split("/")

# transform as:nn community format to int for gobgp
def std_comm_to_int(comm):
    #AS 5434995
    # 5434995 / 65536 = 82
    # 5434995 - (82 * 65536) = 61043
    # asdot = 82.61043
    as_n, nn = map(int, comm.split(":"))
    res = nn + (as_n * 65536)
    return res

# format large communities
def large_comm_format(comm):
    components = comm.split(":")
    return list(map(int, components))

# not used currently
def ext_comm_format(comm):
    hex_repr = "{:016x}".format(comm)
    oct1 = hex_repr[:2]
    oct2 = hex_repr[2:4]
    val = hex_repr[4:]
    return "Type is {}, subtype is {}, value is {}".format(oct1, oct2, val)

class GoBgpGo():
    def __init__(self, destination, port):
        self.channel = grpc.insecure_channel(str(destination) + ":" + str(port))
        self.stub = gobgp_pb2_grpc.GobgpApiStub(self.channel)
        
    def send_update(self, pfx, path_attrs):
        subnet, pfx_len = get_pfx_len(pfx)
        nlri = Any()
        nlri.Pack(attribute_pb2.IPAddressPrefix(
            prefix_len=int(pfx_len),
            prefix=subnet,
        ))
        attributes = []
        for key, value in path_attrs.items():
            # Origin attribute
            if key == "ORIGIN":
                target_orig = int(list(value.keys())[0])
                origin = Any()
                origin.Pack(attribute_pb2.OriginAttribute(
                    origin=target_orig,
                ))
                attributes.append(origin)
            # AS PATH
            if key == "AS_PATH":
                as_segment = attribute_pb2.AsSegment(
                    # type=2,  # "type" causes syntax error
                    numbers=list(map(int,value[0]['value'])),
                )
                as_segment.type = int(list(value[0]['type'].keys())[0])
                as_path = Any()
                as_path.Pack(attribute_pb2.AsPathAttribute(
                    segments=[as_segment],
                ))
                attributes.append(as_path)
            # MED attribute
            if key == "MULTI_EXIT_DISC":
                med_target = Any()
                med_target.Pack(attribute_pb2.MultiExitDiscAttribute(
                    med=value,
                ))
                attributes.append(med_target)
            # Standard communities - converted from as:nn to int
            if key == "COMMUNITY":
                std_comm = Any()
                std_comm.Pack(attribute_pb2.CommunitiesAttribute(
                    communities=map(std_comm_to_int,value),
                ))
                attributes.append(std_comm)
            # Extended community, passed for now
            if key == "EXTENDED COMMUNITIES":
                pass
            # Large communities
            if key == "LARGE_COMMUNITY":
                lrg_comms = []
                for comm in value:
                    comm_ints = large_comm_format(comm)
                    lrg_comms.append(attribute_pb2.LargeCommunity(
                        global_admin = comm_ints[0],
                        local_data1 = comm_ints[1],
                        local_data2 = comm_ints[2],
                    ))
                large_comm = Any()
                large_comm.Pack(attribute_pb2.LargeCommunitiesAttribute(
                    communities = lrg_comms,
                ))
                attributes.append(large_comm)

        # default is to set nexthop to local GoBGP address
        next_hop = Any()
        next_hop.Pack(attribute_pb2.NextHopAttribute(next_hop="0.0.0.0"))
        attributes.append(next_hop)
        
        # IPv4 unicast AFI/SAFI
        if ipaddress.ip_network(pfx).version == 4:
            self.stub.AddPath(
                gobgp_pb2.AddPathRequest(
                    table_type=gobgp_pb2.GLOBAL,
                    path=gobgp_pb2.Path(
                        nlri=nlri,
                        pattrs=attributes,
                        family=gobgp_pb2.Family(afi=gobgp_pb2.Family.AFI_IP, safi=gobgp_pb2.Family.SAFI_UNICAST),
                    )
                ),
                _TIMEOUT_SECONDS,
            )
        # IPv6 unicast AFI/SAFI
        elif ipaddress.ip_network(pfx).version == 6:
            self.stub.AddPath(
                gobgp_pb2.AddPathRequest(
                    table_type=gobgp_pb2.GLOBAL,
                    path=gobgp_pb2.Path(
                        nlri=nlri,
                        pattrs=attributes,
                        family=gobgp_pb2.Family(afi=gobgp_pb2.Family.AFI_IP6, safi=gobgp_pb2.Family.SAFI_UNICAST),
                    )
                ),
                _TIMEOUT_SECONDS,
            )