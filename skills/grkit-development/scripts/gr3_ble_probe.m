#import <Foundation/Foundation.h>
#import <AppKit/AppKit.h>
#import <CoreBluetooth/CoreBluetooth.h>
@interface Probe : NSObject<CBCentralManagerDelegate,CBPeripheralDelegate>
@property CBCentralManager *manager;
@property CBPeripheral *camera;
@property NSMutableArray *reads;
@property NSInteger pending;
@property CBCharacteristic *current;
@property NSString *logPath;
@property NSTimeInterval duration;
@property BOOL finished;
@end
@implementation Probe
-(void)log:(NSString*)s { NSString *line=[NSString stringWithFormat:@"%@ %@\n",[NSDate date],s]; NSFileHandle *h=[NSFileHandle fileHandleForWritingAtPath:self.logPath]; [h seekToEndOfFile]; [h writeData:[line dataUsingEncoding:NSUTF8StringEncoding]]; [h closeFile]; }
-(void)finish:(NSString*)reason { if(self.finished)return; self.finished=YES; [self log:reason]; [self.manager stopScan]; if(self.camera)[self.manager cancelPeripheralConnection:self.camera]; dispatch_after(dispatch_time(DISPATCH_TIME_NOW,NSEC_PER_SEC),dispatch_get_main_queue(),^{[NSApp terminate:nil];}); }
-(void)start { [@"" writeToFile:self.logPath atomically:YES encoding:NSUTF8StringEncoding error:nil]; self.reads=[NSMutableArray array]; [self log:@"START read-only BLE; Wi-Fi unchanged"]; self.manager=[[CBCentralManager alloc]initWithDelegate:self queue:dispatch_get_main_queue()]; dispatch_after(dispatch_time(DISPATCH_TIME_NOW,(int64_t)(self.duration*NSEC_PER_SEC)),dispatch_get_main_queue(),^{[self finish:@"END bounded capture completed"];}); }
-(void)centralManagerDidUpdateState:(CBCentralManager*)c { [self log:[NSString stringWithFormat:@"STATE %ld authorization %ld",(long)c.state,(long)CBManager.authorization]]; if(c.state==CBManagerStateUnauthorized||c.state==CBManagerStateUnsupported||c.state==CBManagerStatePoweredOff){[self finish:@"END Bluetooth unavailable"];return;} if(c.state==CBManagerStatePoweredOn){[c scanForPeripheralsWithServices:nil options:nil]; [self log:@"SCANNING"];}}
-(void)centralManager:(CBCentralManager*)c didDiscoverPeripheral:(CBPeripheral*)p advertisementData:(NSDictionary*)ad RSSI:(NSNumber*)rssi { NSString *name=ad[CBAdvertisementDataLocalNameKey]?:p.name?:@""; NSString *u=name.uppercaseString; NSArray *ss=ad[CBAdvertisementDataServiceUUIDsKey]?:@[]; BOOL match=[u containsString:@"RICOH"]||[u hasPrefix:@"GR"]; for(CBUUID *uuid in ss)if([uuid.UUIDString.uppercaseString isEqual:@"9A5ED1C5-74CC-4C50-B5B6-66A48E7CCFF1"])match=YES; if(!match||self.camera)return; self.camera=p; p.delegate=self; [self log:[NSString stringWithFormat:@"CAMERA matched RICOH/GR advertisement RSSI %@ services %@",rssi,ss]]; [c stopScan]; [c connectPeripheral:p options:nil]; }
-(void)centralManager:(CBCentralManager*)c didConnectPeripheral:(CBPeripheral*)p { [self log:@"CONNECTED"]; [p discoverServices:nil]; }
-(void)centralManager:(CBCentralManager*)c didFailToConnectPeripheral:(CBPeripheral*)p error:(NSError*)e { [self log:[NSString stringWithFormat:@"CONNECT ERROR %@",e]]; [self finish:@"END connect failed"]; }
-(void)centralManager:(CBCentralManager*)c didDisconnectPeripheral:(CBPeripheral*)p error:(NSError*)e { [self log:[NSString stringWithFormat:@"DISCONNECTED %@",e]]; [self finish:@"END disconnected; no automatic retries"]; }
-(void)peripheral:(CBPeripheral*)p didDiscoverServices:(NSError*)e { [self log:[NSString stringWithFormat:@"SERVICES %@ error %@",p.services,e]]; if(e){[self finish:@"END service discovery failed"];return;} self.pending=p.services.count; for(CBService*s in p.services)[p discoverCharacteristics:nil forService:s]; }
-(void)next { if(self.current||self.finished)return; if(self.reads.count){ CBCharacteristic *ch=self.reads.firstObject; [self.reads removeObjectAtIndex:0]; self.current=ch; [self.camera readValueForCharacteristic:ch]; dispatch_after(dispatch_time(DISPATCH_TIME_NOW,8*NSEC_PER_SEC),dispatch_get_main_queue(),^{if(self.current==ch)[self finish:@"END ATT read timeout; discard late replies"];}); }else{[self log:@"READS COMPLETE"];}}
-(void)peripheral:(CBPeripheral*)p didDiscoverCharacteristicsForService:(CBService*)s error:(NSError*)e { if(e){[self finish:@"END characteristic discovery failed"];return;} NSSet *safe=[NSSet setWithArray:@[@"35FE6272-6AA5-44D9-88E1-F09427F51A71",@"B4EB8905-7411-40A6-A367-2834C2157EA7",@"875FC41D-4980-434C-A653-FD4A4D4410C4",@"1452335A-EC7F-4877-B8AB-0F72E18BB295",@"CDFC734E-EA21-427D-A69F-C1A0F7F1E9A3"]]; for(CBCharacteristic*ch in s.characteristics){[self log:[NSString stringWithFormat:@"CHAR %@ props %lu",ch.UUID,(unsigned long)ch.properties]]; if([safe containsObject:ch.UUID.UUIDString.uppercaseString]&&(ch.properties&CBCharacteristicPropertyRead))[self.reads addObject:ch]; if(([ch.UUID.UUIDString.uppercaseString isEqual:@"CDFC734E-EA21-427D-A69F-C1A0F7F1E9A3"]||[ch.UUID.UUIDString.uppercaseString isEqual:@"1452335A-EC7F-4877-B8AB-0F72E18BB295"])&&(ch.properties&CBCharacteristicPropertyNotify))[p setNotifyValue:YES forCharacteristic:ch];} if(--self.pending==0)[self next]; }
-(void)peripheral:(CBPeripheral*)p didUpdateNotificationStateForCharacteristic:(CBCharacteristic*)ch error:(NSError*)e { [self log:[NSString stringWithFormat:@"NOTIFY %@ enabled %d error %@",ch.UUID,ch.isNotifying,e]]; }
-(void)peripheral:(CBPeripheral*)p didUpdateValueForCharacteristic:(CBCharacteristic*)ch error:(NSError*)e { [self log:[NSString stringWithFormat:@"READ %@ data %@ error %@",ch.UUID,ch.value,e]]; if(self.current==ch){self.current=nil; [self next];} }
@end
int main(int argc,const char *argv[]){ @autoreleasepool {
 NSString *path=NSProcessInfo.processInfo.environment[@"GR3_BLE_LOG"];
 double duration=[NSProcessInfo.processInfo.environment[@"GR3_BLE_SECONDS"] doubleValue];
 if(!path.length||duration<10||duration>600){fprintf(stderr,"Set GR3_BLE_LOG to an absolute log path and GR3_BLE_SECONDS to 10..600.\n");return 2;}
 if(![path isAbsolutePath])return 2;
 [NSApplication sharedApplication]; [NSApp setActivationPolicy:NSApplicationActivationPolicyAccessory];
 Probe*p=[Probe new]; p.logPath=path; p.duration=duration; [p start]; [NSApp run];
 }return 0;}
