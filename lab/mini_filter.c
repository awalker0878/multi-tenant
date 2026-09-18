/* Original test-fixture helper. NOT a production firewall manager.
 * Uses installed Linux UAPI headers; no shell or external library dependencies.
 * Refuses the host network namespace and requires the parent's namespace identity.
 * The Python lab owns every namespace and destroys it at completion.
 */
#define _GNU_SOURCE
#include <arpa/inet.h>
#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <unistd.h>
#include <linux/netfilter_ipv4/ip_tables.h>
#include <linux/netfilter_ipv6/ip6_tables.h>
#include <linux/netfilter/xt_conntrack.h>

#define BUFSIZE (256*1024)
static unsigned char entries[BUFSIZE];
static unsigned int used=0,count=0,hooks[5],under[5];
static int v6=0;
static void fail(const char *s) { perror(s); exit(2); }
static void invalid(const char *s) { fprintf(stderr,"%s\n",s); exit(2); }
static void guard(void) {
 char own[96]={0};
 const char *expected=getenv("HOSTING_LAB_NETNS");
 const char *original=getenv("HOSTING_LAB_ORIGINAL_NETNS");
 if(readlink("/proc/self/ns/net",own,sizeof(own)-1)<0) fail("namespace identity");
 if(!expected || !original || strncmp(original,"net:[",5) || strcmp(own,expected) || !strcmp(own,original)) invalid("Refusing non-fixture network namespace.");

 /* Authorization is restricted to disposable namespaces; environment is not risk approval. */
}
static void *room(size_t n) {
 if(used+n>BUFSIZE) invalid("Rule set exceeds fixture limit.");
 void *p=entries+used; memset(p,0,n); used+=(unsigned)n; return p;
}
static void iface(char *dest,unsigned char *mask,const char *src) {
 if(!src || !strcmp(src,"-")) return;
 size_t n=strlen(src); if(n>=IFNAMSIZ) invalid("Interface name too long.");
 memcpy(dest,src,n+1); memset(mask,0xff,n+1);
}
static void rule(int proto,const char *src,const char *dst,int port,int state,int verdict,const char *in,const char *out) {
 size_t start=used,base=v6?sizeof(struct ip6t_entry):sizeof(struct ipt_entry);
 void *entry=room(base);
 if(v6) {
  struct ip6t_entry *e=entry;
  if(src && inet_pton(AF_INET6,src,&e->ipv6.src)!=1) invalid("Invalid IPv6 source.");
  if(dst && inet_pton(AF_INET6,dst,&e->ipv6.dst)!=1) invalid("Invalid IPv6 destination.");
  if(src) memset(&e->ipv6.smsk,0xff,16); if(dst) memset(&e->ipv6.dmsk,0xff,16);
  e->ipv6.proto=proto; if(proto) e->ipv6.flags=IP6T_F_PROTO;
  iface(e->ipv6.iniface,e->ipv6.iniface_mask,in); iface(e->ipv6.outiface,e->ipv6.outiface_mask,out);
 } else {
  struct ipt_entry *e=entry;
  if(src && inet_pton(AF_INET,src,&e->ip.src)!=1) invalid("Invalid IPv4 source.");
  if(dst && inet_pton(AF_INET,dst,&e->ip.dst)!=1) invalid("Invalid IPv4 destination.");
  if(src) e->ip.smsk.s_addr=0xffffffff; if(dst) e->ip.dmsk.s_addr=0xffffffff;
  e->ip.proto=proto;
  iface(e->ip.iniface,e->ip.iniface_mask,in); iface(e->ip.outiface,e->ip.outiface_mask,out);
 }
 if(state) {
  size_t n=XT_ALIGN(sizeof(struct xt_entry_match))+XT_ALIGN(sizeof(struct xt_conntrack_mtinfo3));
  struct xt_entry_match *m=room(n);m->u.user.match_size=n;strcpy(m->u.user.name,"conntrack");m->u.user.revision=3;
  struct xt_conntrack_mtinfo3 *c=(void *)m->data;c->match_flags=XT_CONNTRACK_STATE;c->state_mask=state;
 }
 if(port) {
  if(proto!=IPPROTO_TCP && proto!=IPPROTO_UDP) invalid("Ports require TCP/UDP.");
  size_t n=XT_ALIGN(sizeof(struct xt_entry_match))+XT_ALIGN(proto==IPPROTO_TCP?sizeof(struct xt_tcp):sizeof(struct xt_udp));
  struct xt_entry_match *m=room(n);m->u.user.match_size=n;strcpy(m->u.user.name,proto==IPPROTO_TCP?"tcp":"udp");
  if(proto==IPPROTO_TCP) {struct xt_tcp *p=(void *)m->data;p->spts[0]=0;p->spts[1]=65535;p->dpts[0]=p->dpts[1]=port;}
  else {struct xt_udp *p=(void *)m->data;p->spts[0]=0;p->spts[1]=65535;p->dpts[0]=p->dpts[1]=port;}
 }
 unsigned target=used-start;
 struct xt_standard_target *t=room(XT_ALIGN(sizeof(*t)));t->target.u.user.target_size=XT_ALIGN(sizeof(*t));t->verdict=-verdict-1;
 if(v6) {struct ip6t_entry *e=entry;e->target_offset=target;e->next_offset=used-start;}
 else {struct ipt_entry *e=entry;e->target_offset=target;e->next_offset=used-start;}
 count++;
}
static void error_end(void) {
 size_t start=used,base=v6?sizeof(struct ip6t_entry):sizeof(struct ipt_entry);void *e=room(base);
 struct xt_error_target *t=room(XT_ALIGN(sizeof(*t)));t->target.u.user.target_size=XT_ALIGN(sizeof(*t));strcpy(t->target.u.user.name,"ERROR");strcpy(t->errorname,"ERROR");
 if(v6){((struct ip6t_entry*)e)->target_offset=base;((struct ip6t_entry*)e)->next_offset=used-start;}
 else {((struct ipt_entry*)e)->target_offset=base;((struct ipt_entry*)e)->next_offset=used-start;} count++;
}
static void rules_file(const char *path,int blocks) {
 FILE *f=fopen(path,"r");if(!f) fail("open rules");char line[512];unsigned line_no=0;
 while(fgets(line,sizeof(line),f)) {
  line_no++;if(!strchr(line,'\n') && !feof(f)) invalid("Oversized rule.");if(line[0]=='#'||line[0]=='\n')continue;
  char act[10],proto[10],src[64],dst[64],in[16],out[16],extra[2];int port;
  if(sscanf(line,"%9s %9s %63s %63s %d %15s %15s %1s",act,proto,src,dst,&port,in,out,extra)!=7) invalid("Malformed fixture rule.");
  int block=!strcmp(act,"block");if(!block && strcmp(act,"allow"))invalid("Invalid fixture action.");
  if(block!=blocks)continue;
  int p=!strcmp(proto,"tcp")?IPPROTO_TCP:!strcmp(proto,"udp")?IPPROTO_UDP:!strcmp(proto,"any")?0:-1;
  if(p<0||port<0||port>65535||(!block&&(!p||!port)))invalid("Invalid fixture protocol/port.");
  if((strchr(src,':')!=NULL)!=v6||(strchr(dst,':')!=NULL)!=v6)continue;
  rule(p,src,dst,port,block?0:8,block?NF_DROP:NF_ACCEPT,in,out);
 }
 if(ferror(f)) fail("read rules");fclose(f);
}
static void install(int s,const char *path,int host,int quarantine,int router) {
 unsigned old_count=0,valid=0;
 if(v6){struct ip6t_getinfo g={0};strcpy(g.name,"filter");socklen_t n=sizeof(g);if(getsockopt(s,IPPROTO_IPV6,IP6T_SO_GET_INFO,&g,&n))fail("get v6 info");old_count=g.num_entries;valid=g.valid_hooks;}
 else {struct ipt_getinfo g={0};strcpy(g.name,"filter");socklen_t n=sizeof(g);if(getsockopt(s,IPPROTO_IP,IPT_SO_GET_INFO,&g,&n))fail("get v4 info");old_count=g.num_entries;valid=g.valid_hooks;}
 if(valid!=14)invalid("Unexpected filter hooks.");memset(hooks,0,sizeof(hooks));memset(under,0,sizeof(under));
 hooks[NF_INET_LOCAL_IN]=used;
 if(!host){rule(0,NULL,NULL,0,0,NF_ACCEPT,"lo",NULL);if(v6)rule(IPPROTO_ICMPV6,NULL,NULL,0,0,NF_ACCEPT,NULL,NULL);}
 under[NF_INET_LOCAL_IN]=used;rule(0,NULL,NULL,0,0,host?NF_ACCEPT:NF_DROP,NULL,NULL);
 hooks[NF_INET_FORWARD]=used;
 if(!host && !quarantine && !router){
  rules_file(path,1); /* containment blocks take precedence over established sessions */
  rule(0,NULL,NULL,0,1,NF_DROP,NULL,NULL); /* INVALID */
  rule(0,NULL,NULL,0,6,NF_ACCEPT,NULL,NULL); /* ESTABLISHED,RELATED */
  rules_file(path,0);
 }
 under[NF_INET_FORWARD]=used;rule(0,NULL,NULL,0,0,router?NF_ACCEPT:NF_DROP,NULL,NULL);
 hooks[NF_INET_LOCAL_OUT]=used;under[NF_INET_LOCAL_OUT]=used;rule(0,NULL,NULL,0,0,NF_ACCEPT,NULL,NULL);error_end();
 struct xt_counters *c=calloc(old_count,sizeof(*c));if(!c)fail("counters allocation");
 if(v6){struct ip6t_replace *r=calloc(1,sizeof(*r)+used);if(!r)fail("replace allocation");strcpy(r->name,"filter");r->valid_hooks=valid;r->num_entries=count;r->size=used;memcpy(r->hook_entry,hooks,sizeof(hooks));memcpy(r->underflow,under,sizeof(under));r->num_counters=old_count;r->counters=c;memcpy(r->entries,entries,used);if(setsockopt(s,IPPROTO_IPV6,IP6T_SO_SET_REPLACE,r,sizeof(*r)+used))fail("set v6 filter");free(r);}
 else {struct ipt_replace *r=calloc(1,sizeof(*r)+used);if(!r)fail("replace allocation");strcpy(r->name,"filter");r->valid_hooks=valid;r->num_entries=count;r->size=used;memcpy(r->hook_entry,hooks,sizeof(hooks));memcpy(r->underflow,under,sizeof(under));r->num_counters=old_count;r->counters=c;memcpy(r->entries,entries,used);if(setsockopt(s,IPPROTO_IP,IPT_SO_SET_REPLACE,r,sizeof(*r)+used))fail("set v4 filter");free(r);}free(c);
 printf("{\"installed\":true,\"family\":%d,\"rules\":%u}\n",v6?6:4,count);
}
static void dump(int s) {
 unsigned size=0,start=0,end=0;
 if(v6){struct ip6t_getinfo g={0};strcpy(g.name,"filter");socklen_t n=sizeof(g);if(getsockopt(s,IPPROTO_IPV6,IP6T_SO_GET_INFO,&g,&n))fail("info");size=g.size;start=g.hook_entry[2];end=g.underflow[2];}
 else {struct ipt_getinfo g={0};strcpy(g.name,"filter");socklen_t n=sizeof(g);if(getsockopt(s,IPPROTO_IP,IPT_SO_GET_INFO,&g,&n))fail("info");size=g.size;start=g.hook_entry[2];end=g.underflow[2];}
 size_t base=v6?sizeof(struct ip6t_get_entries):sizeof(struct ipt_get_entries);void *buf=calloc(1,base+size);if(!buf)fail("dump allocation");strcpy(buf,"filter");*((unsigned*)((char*)buf+32))=size;socklen_t n=base+size;
 if(getsockopt(s,v6?IPPROTO_IPV6:IPPROTO_IP,65,buf,&n))fail("entries");
 uint64_t drop=0,accept=0;unsigned off=0;
 while(off<size){unsigned next,target;struct xt_counters c;
  if(v6){struct ip6t_entry *e=(void*)((char*)buf+base+off);next=e->next_offset;target=e->target_offset;c=e->counters;}
  else {struct ipt_entry *e=(void*)((char*)buf+base+off);next=e->next_offset;target=e->target_offset;c=e->counters;}
  if(!next||off+next>size)invalid("Corrupt fixture table.");
  struct xt_standard_target *t=(void*)((char*)buf+base+off+target);
  if(off>=start&&off<=end&&t->target.u.user.name[0]==0){if(t->verdict==-1)drop+=c.pcnt;else if(t->verdict==-2)accept+=c.pcnt;}
  off+=next;
 }
 printf("{\"family\":%d,\"forward_dropped_packets\":%llu,\"forward_accepted_packets\":%llu}\n",v6?6:4,(unsigned long long)drop,(unsigned long long)accept);free(buf);
}
int main(int argc,char **argv) {
 guard();if(argc<3|| (strcmp(argv[1],"4")&&strcmp(argv[1],"6")))invalid("usage: mini_filter 4|6 dump|install rules host|edge|quarantine|router");
 v6=!strcmp(argv[1],"6");int s=socket(v6?AF_INET6:AF_INET,SOCK_RAW,IPPROTO_RAW);if(s<0)fail("socket");
 if(!strcmp(argv[2],"dump"))dump(s);
 else if(argc==5&&!strcmp(argv[2],"install")&&(!strcmp(argv[4],"host")||!strcmp(argv[4],"edge")||!strcmp(argv[4],"quarantine")||!strcmp(argv[4],"router"))) install(s,argv[3],!strcmp(argv[4],"host"),!strcmp(argv[4],"quarantine"),!strcmp(argv[4],"router"));
 else invalid("Invalid fixture arguments.");close(s);return 0;
}
