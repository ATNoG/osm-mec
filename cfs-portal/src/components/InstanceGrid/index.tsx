import { useMemo } from 'react';
import {
  MaterialReactTable,
  useMaterialReactTable,
  type MRT_ColumnDef,
} from 'material-react-table';

import { useEffect, useState } from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import { Tooltip, LinearProgress, Skeleton } from "@mui/material";
import { getAppI, terminateAppI } from "../../api/api";
import { DropdownOption, OperationalStatus, ConfigStatus, ActionType, Item, InstanceGridProps, Metrics, RowData } from "../../types/Component";
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import CancelIcon from '@mui/icons-material/Cancel';
import AccessTimeFilledIcon from '@mui/icons-material/AccessTimeFilled';
import StopCircleIcon from '@mui/icons-material/StopCircle';
import toast from "../../utils/toast";
import DetailsDialog from "../Dialog/DetailsDialog";
import ConfirmationDialog from "../Dialog/ConfirmationDialog";
import DropdownButton from "../../components/DropdownButton";

const renderOperationalStatus = (status: OperationalStatus) => {
    switch (status) {
        case OperationalStatus.INIT:
            return <AccessTimeFilledIcon color='warning' />
        case OperationalStatus.RUNNING:
            return <CheckCircleIcon color='success' />
        case OperationalStatus.FAILED:
            return <CancelIcon color='error' />
        default:
            return <StopCircleIcon sx={{ color: '#aaa' }} />;
    }
}

const renderConfigStatus = (status: ConfigStatus) => {
    switch (status) {
        case ConfigStatus.INIT:
            return <AccessTimeFilledIcon color='warning' />
        case ConfigStatus.CONFIGURED:
            return <CheckCircleIcon color='success' />
        case ConfigStatus.FAILED:
            return <CancelIcon color='error' />
        default:
            return <StopCircleIcon sx={{ color: '#aaa' }} />;
    }
}

const terminateInstance = async (id: string) => {
    try {
        await terminateAppI(id);
        toast.success('Instance terminated successfully');
    } catch (error) {
        toast.error('Error terminating instance');
    }
}

const InstanceGrid = ({ minimalConfig = false, instanceCount }: InstanceGridProps) => {
    // Data rows variables
    const [instanceData, setInstanceData] = useState<RowData[]>([]);
    const [expandedRows, setExpandedRows] = useState<{ [key: string]: boolean }>({});
    const [metrics, setMetrics] = useState<Metrics | null>(null);
    // const [rowData, setRowData] = useState<RowData[]>([]);

    // Dialog variables
    const [loading, setLoading] = useState(true);
    // const [loading, setLoading] = useState(false);
    const [detailsDialogOpen, setDetailsDialogOpen] = useState(false);
    const [detailsData, setDetailsData] = useState('');
    const [confirmationDialogOpen, setConfirmationDialogOpen] = useState(false);
    const [id, setId] = useState('');
    const [socket, setSocket] = useState<WebSocket | null>(null);

    // Get the color of the load based on the value
    const getLoadColor = (load: number) => {
        if (load < 40) {
            return 'success';
        } else if (load < 75) {
            return 'warning';
        } else {
            return 'error';
        }
    }

    const formatInstanceData = (data: any) => {
        const formattedData: RowData[] = [];
        for (const appi of data) {
            // Add the App Instance as a row
            formattedData.push({
                id: appi["appi_id"],
                name: appi.name,
                description: appi.description || null, // Ensure description is not undefined
                details: appi.details || null, // Ensure details is not undefined
                'current-meh': {"domain": appi.domain, "cluster": null, "node": null}, // Ensure current-meh is not undefined
                'cpu-load': null, // Placeholder for CPU load
                'mem-load': null, // Placeholder for Memory load
                latency: null, // Placeholder for latency
                'created-at': new Date(appi['created-at']),
                'operational-status': appi['operational-status'] || OperationalStatus.INIT, // Default to INIT if not provided
                'config-status': appi['config-status'] || ConfigStatus.INIT, // Default to INIT if not provided
                warnings: null, // Placeholder for warnings
                appiId: null
            });
            
            const kduNodes: Record<string, any> = {};
            for (const [domainKey, domainValue] of Object.entries(appi.instances as Record<string, any>)) {
                for (const [clusterKey, clusterValue] of Object.entries(domainValue as Record<string, any>)) {
                    for (const [kduKey, node] of Object.entries(clusterValue.kdus)) {
                        kduNodes[kduKey] = {"domain": domainKey, "cluster": clusterKey, "node": node}
                    }
                }
            }

            for (const [kduKey, kduValue] of Object.entries(appi.kdus as Record<string, any>)){
                // Skip if the KDU is not enabled
                if (!kduValue.enable) {
                    continue; 
                }
                
                // Add each container as a sub-row
                formattedData.push({
                    id: kduKey,
                    name: kduValue.name,
                    description: `kdu: ${kduValue.name} helm-chart: ${kduValue["helm-chart"]} helm-version: ${kduValue["helm-version"]}`,
                    details: '',
                    'current-meh': kduNodes[kduKey],
                    'cpu-load': null,
                    'mem-load': null,
                    latency: null,
                    'created-at': kduValue.enable ? new Date(appi['created-at']) : null,
                    'operational-status': kduValue.status || OperationalStatus.INIT,
                    'config-status': kduValue.enable ? ConfigStatus.CONFIGURED : ConfigStatus.FAILED,
                    warnings: kduValue.warning || null,
                    appiId: appi["appi_id"]
                });
            }
        }
        console.log("Formatted Data: ", formattedData);

        return formattedData;
    }

    // Get the Rows to show in the DataGrid
    const getInstanceData = async () => {
        try {
            const { data } = await getAppI();
            const formattedData = formatInstanceData(data);
            setInstanceData(formattedData);
            if (instanceCount)
                instanceCount(data.length);
        } catch (error) {
            toast.error('Error fetching instance data');
            setInstanceData([]);
            if (instanceCount)
                instanceCount(0);
        } finally {
            setLoading(false);
        }
    };

    // Get Instance Data each 5 seconds
    useEffect(() => {
        const fetchData = async () => {
            getInstanceData();
        };

        fetchData();
        const interval = setInterval(fetchData, 5000);
        return () => clearInterval(interval);
    }, []);

    // Create WebSocket connection
    useEffect(() => {
        const ws = new WebSocket(`ws://${process.env.REACT_APP_OSS_HOST || 'localhost'}:${process.env.REACT_APP_WS_SOCKET_PORT || '8001'}`);
        setSocket(ws);
        ws.onclose = () => {
            setTimeout(() => {
                setSocket(new WebSocket(ws.url)); // Reconnect after delay
            }, 3000);
        };
    }, []);

    // Listen for WebSocket messages and process the message
    useEffect(() => {
        if (socket) {
            socket.onopen = () => {
                console.log('Connected to WebSocket');
            };
            socket.onmessage = (event: any) => {
                const data: Metrics = event.data ? JSON.parse(event.data) : {};
                setMetrics((prevMetrics: any) => {
                    return data;
                });
            };
            socket.onclose = () => {
                console.log('Disconnected from WebSocket');
            };
        }
    }, [socket]);

    const columns: MRT_ColumnDef<any>[] = [
        {
            id: 'name', 
            header: 'Name',
            accessorKey: 'name',
            enableColumnActions: false,
            muiTableHeadCellProps: () => ({
                align: 'left' as const,
                sx: { minWidth: '180px', Width: '180px', maxWidth: '180px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis'},
            }),
            muiTableBodyCellProps: () => ({
                align: 'left' as const,
                sx: { minWidth: '180px', Width: '180px', maxWidth: '180px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis'},
            }),
            Cell: ({ row }: any) => (
                <Tooltip title={ row.original.name }>
                    <Typography variant="body2" noWrap sx={{ width: '100%', overflow: 'hidden', textOverflow: 'ellipsis'}}>
                        {row.original.name}
                    </Typography>
                </Tooltip>
            ),
        },
        ...minimalConfig ? [] : [
            {
                header: 'Description',
                accessorKey: 'description',
                enableColumnActions: false,
                muiTableHeadCellProps: () => ({
                    align: 'left' as const,
                    sx: { minWidth: '300px', Width: '300px', maxWidth: '300px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis'},
                }),
                muiTableBodyCellProps: () => ({
                    align: 'left' as const,
                    sx: { minWidth: '300px', Width: '300px', maxWidth: '300px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis'},
                }),
                Cell: ({ row }: any) => (
                    <Tooltip title={ row.original.description }>
                        <Typography variant="body2" noWrap sx={{ width: '100%', overflow: 'hidden', textOverflow: 'ellipsis'}}>
                            {row.original.description}
                        </Typography>
                    </Tooltip>
                ),
            }
        ],
        ...minimalConfig ? [] : [
            {
                header: 'Details',
                accessorKey: 'details',
                enableColumnActions: false,
                muiTableHeadCellProps: () => ({
                    align: 'left' as const,
                    sx: { minWidth: '200px', Width: '200px', maxWidth: '200px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis'},
                }),
                muiTableBodyCellProps: () => ({
                    align: 'left' as const,
                    sx: { minWidth: '200px', Width: '200px', maxWidth: '200px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis'},
                }),
                Cell: ({row}: any) => (
                    <Tooltip title={ row.original.details }>
                        <Typography variant="body2" noWrap sx={{ width: '100%', overflow: 'hidden', textOverflow: 'ellipsis'}}>
                            {row.original.details}
                        </Typography>
                    </Tooltip>
                )
            }
        ],
        {
            header: 'Domain/Node',
            accessorKey: 'current-meh',
            enableColumnActions: false,
            muiTableHeadCellProps: () => ({
                align: 'center' as const,
                sx: { minWidth: '180px', Width: '180px', maxWidth: '180px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis'},
            }),
            muiTableBodyCellProps: () => ({
                align: 'center' as const,
                sx: { minWidth: '180px', Width: '180px', maxWidth: '180px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis'},
            }),
            Cell: ({row}: any) => {
                const domain = row.original['current-meh'].domain;
                const cluster = row.original['current-meh'].cluster;
                const node = row.original['current-meh'].node;

                if (row.original.appiId !== undefined && row.original.appiId !== null) {
                    return (
                        <>
                            <Tooltip title={ "Domain: " + domain + ", Cluster: " + cluster + ", Node: " + node }>
                                <Typography variant="body2" noWrap sx={{ width: '100%', overflow: 'hidden', textOverflow: 'ellipsis'}}>
                                    {node || domain || '-'}
                                </Typography>
                            </Tooltip>
                        </>
                    );
                }

                return (
                    <Box sx={{ position: 'relative', width: '100%' }}>
                        <Tooltip title={ "Domain: " + domain}>
                            <Typography variant="body2" noWrap sx={{ width: '100%', overflow: 'hidden', textOverflow: 'ellipsis'}}>
                                {node || domain || '-'}
                            </Typography>
                        </Tooltip>
                    </Box>
                )
            }
        },
        {
            header: 'CPU (%)',
            accessorKey: 'cpu-load',
            enableColumnActions: false,
            muiTableHeadCellProps: () => ({
                align: 'center' as const,
                sx: { minWidth: '100px', Width: '100px', maxWidth: '100px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis'},
            }),
            muiTableBodyCellProps: () => ({
                align: 'center' as const,
                sx: { minWidth: '100px', Width: '100px', maxWidth: '100px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis'},
            }),
            Cell: ({row}: any) => {
                let metricsData;
                if (row.original.appiId !== undefined && row.original.appiId !== null && metrics && metrics.appis[row.original.appiId] && metrics.appis[row.original.appiId].artifacts[row.original.name] && metrics.appis[row.original.appiId].artifacts[row.original.name].metrics) {
                    metricsData = metrics.appis[row.original.appiId].artifacts[row.original.name].metrics;
                }
                const cpuLoad: string = metricsData ? metricsData['cpu-load'] : null;
                return (
                    <Box sx={{ position: 'relative', width: '60%', display: 'flex', margin: '0 auto', alignItems: 'center', justifyContent: 'center'}}>
                        {cpuLoad !== undefined && cpuLoad !== null ? (
                            <>
                                <LinearProgress
                                    variant="determinate"
                                    value={Number(cpuLoad)}
                                    sx={{ width: '100%', height: '30px' }}
                                    color={getLoadColor(Number(cpuLoad))}
                                />
                                <Tooltip title={ cpuLoad }>
                                    <Typography
                                        variant="body2"
                                        fontWeight='bold'
                                        sx={{
                                            position: 'absolute',
                                            top: 0,
                                            left: '50%',
                                            transform: 'translateX(-50%)',
                                            width: '100%',
                                            textAlign: 'center',
                                            lineHeight: '30px'
                                        }}
                                    >
                                        {cpuLoad}
                                    </Typography>
                                </Tooltip>
                            </>) : (
                            <Typography variant="body2" textAlign='center'>
                                -
                            </Typography>
                        )}
                    </Box>
                )
            }
        },
        {
            header: 'Mem (%)',
            accessorKey: 'mem-load',
            enableColumnActions: false,
            muiTableHeadCellProps: () => ({
                align: 'center' as const,
                sx: { minWidth: '100px', Width: '100px', maxWidth: '100px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis'},
            }),
            muiTableBodyCellProps: () => ({
                align: 'center' as const,
                sx: { minWidth: '100px', Width: '100px', maxWidth: '100px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis'},
            }),
            Cell: ({row}: any) => {
                let metricsData;
                if (row.original.appiId !== undefined && row.original.appiId !== null && metrics && metrics.appis[row.original.appiId] && metrics.appis[row.original.appiId].artifacts[row.original.name] && metrics.appis[row.original.appiId].artifacts[row.original.name].metrics) {
                    metricsData = metrics.appis[row.original.appiId].artifacts[row.original.name].metrics;
                }
                const memLoad: string = metricsData ? metricsData['mem-load'] : null;
                return (
                    <Box sx={{ position: 'relative', width: '60%', display: 'flex', margin: '0 auto', alignItems: 'center', justifyContent: 'center'}}>
                        {memLoad !== undefined && memLoad !== null ? (
                            <>
                                <LinearProgress
                                    variant="determinate"
                                    value={Number(memLoad)}
                                    sx={{ width: '100%', height: '30px' }}
                                    color={getLoadColor(Number(memLoad))}
                                />
                                <Tooltip title={ memLoad }>
                                    <Typography
                                        variant="body2"
                                        fontWeight='bold'
                                        sx={{
                                            position: 'absolute',
                                            top: 0,
                                            left: '50%',
                                            transform: 'translateX(-50%)',
                                            width: '100%',
                                            textAlign: 'center',
                                            lineHeight: '30px'
                                        }}
                                        >
                                        {memLoad}
                                    </Typography>
                                </Tooltip>
                            </>) : (
                            <Typography variant="body2" textAlign='center'>
                                -
                            </Typography>
                        )}
                    </Box>
                )
            }
        },
        {
            header: 'Latency',
            accessorKey: 'latency',
            enableColumnActions: false,
            muiTableHeadCellProps: () => ({
                align: 'center' as const,
                sx: { minWidth: '100px', Width: '100px', maxWidth: '100px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis'},
            }),
            muiTableBodyCellProps: () => ({
                align: 'center' as const,
                sx: { minWidth: '100px', Width: '100px', maxWidth: '100px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis'},
            }),
            Cell: ({row}: any) => {
                const latency: string = row.original.latency;
                const color=getLoadColor(Number(latency));
                return (
                    <>
                        {latency !== undefined && latency !== null ? (
                            <Tooltip title={ latency }>
                                <Typography variant="body2" noWrap sx={(theme) => ({width: '100%', overflow: 'hidden', textOverflow: 'ellipsis', color: theme.palette[color].main, fontWeight: 'bold'})}>
                                    {latency}
                                </Typography>
                            </Tooltip>
                        ) : (
                            <Typography variant="body2" textAlign='center'>
                                -
                            </Typography>
                        )}
                    </>
                )
            }
        },
        ...minimalConfig ? [] : [
            {
                accessorKey: 'created-at',
                header: 'Created At',
                // size: 20,
                enableColumnActions: false,
                muiTableHeadCellProps: () => ({
                    align: 'center' as const,
                    sx: { minWidth: '120px', Width: '120px', maxWidth: '120px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis'},
                }),
                muiTableBodyCellProps: () => ({
                    align: 'center' as const,
                    sx: { minWidth: '120px', Width: '120px', maxWidth: '120px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis'},
                }),
                Cell: ({ row }: any) => {
                    const rawDate = row.original['created-at'];
                    if (!rawDate) {
                        return (
                            <Typography variant="body2" textAlign="center">
                                -
                            </Typography>
                        );  
                    }
                    const date = new Date(rawDate);
                    return (
                        <Tooltip title={date.toLocaleString('en-GB')}>
                            <Typography variant="body2">
                                {date.toLocaleDateString('en-GB')}
                            </Typography>
                        </Tooltip>
                    );
                }                
            }
        ],
        {
            header: 'Operational Status',
            accessorKey: 'operational-status',
            enableSorting: false,
            enableColumnActions: false,
            muiTableHeadCellProps: () => ({
                align: 'center' as const,
                sx: { minWidth: '130px', Width: '130px', maxWidth: '130px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis'},
            }),
            muiTableBodyCellProps: () => ({
                align: 'center' as const,
                sx: { minWidth: '130px', Width: '130px', maxWidth: '130px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis'},
            }),
            Cell: ({ row }: any) => (
                row.original['operational-status'] !== undefined && row.original['operational-status'] !== null ? (
                    <Tooltip title={row.original['operational-status']}>
                        {renderOperationalStatus(row.original['operational-status'] as OperationalStatus)}
                    </Tooltip>
                ) : (
                    <Typography variant="body2" textAlign='center'>
                        -
                    </Typography>
                )
            )
        },
        ...minimalConfig ? [] : [
            {
                accessorKey: 'config-status',
                header: 'Config Status',
                enableSorting: false,
                enableColumnActions: false,
                muiTableHeadCellProps: () => ({
                    align: 'center' as const,
                    sx: { minWidth: '100px', Width: '100px', maxWidth: '100px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis'},
                }),
                muiTableBodyCellProps: () => ({
                    align: 'center' as const,
                    sx: { minWidth: '100px', Width: '100px', maxWidth: '100px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis'},
                }),
                Cell: ({ row }: any) => (
                    row.original['config-status'] !== undefined && row.original['config-status'] !== null ? (
                        <Tooltip title={row.original['config-status']}>
                            {renderConfigStatus(row.original['config-status'] as ConfigStatus)}
                        </Tooltip>
                    ) : (
                        <Typography variant="body2" textAlign='center'>
                            -
                        </Typography>
                    )
                )
            }
        ],
        ...minimalConfig ? [] : [
            {
                header: 'Warnings',
                accessorKey: 'warnings',
                enableSorting: false,
                enableColumnActions: false,
                muiTableHeadCellProps: () => ({
                    align: 'center' as const,
                    sx: { minWidth: '100px', Width: '100px', maxWidth: '100px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis'},
                }),
                muiTableBodyCellProps: () => ({
                    align: 'center' as const,
                    sx: { minWidth: '100px', Width: '100px', maxWidth: '100px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis'},
                }),
                Cell: ({ row }: any) => {
                    const warning = row.original.warnings;
                    if (warning !== undefined && warning !== null) {
                        return (
                            <Tooltip title={warning}>
                                <Box display="flex" alignItems="center" justifyContent="center">
                                    {renderOperationalStatus(OperationalStatus.FAILED)}
                                </Box>
                            </Tooltip>
                        );
                    }
                    else{
                        return (
                            <Typography variant="body2" textAlign='center'>
                                -
                            </Typography>
                        );
                    }

                }
            }
        ],
        ...minimalConfig ? [] : [
            {
                header: 'Actions',
                accessorKey: 'actions',
                enableSorting: false,
                enableColumnActions: false,
                muiTableHeadCellProps: () => ({
                    align: 'center' as const,
                    sx: { minWidth: '70px', Width: '70px', maxWidth: '70px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis'},
                }),
                muiTableBodyCellProps: () => ({
                    align: 'center' as const,
                    sx: { minWidth: '70px', Width: '70px', maxWidth: '70px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis'},
                }),
                Cell: ({ row }: any) => (
                    (
                        row.original.appiId === null ?
                        (
                            <DropdownButton
                                options={
                                    [
                                        {
                                            label: 'Terminate',
                                            handleClick: () => {
                                                setConfirmationDialogOpen(true);
                                                setId(row.original.id as string);
                                            }
                                        },
                                    ] as DropdownOption[]
                                }
                            />
                        ) : null
                    )
                )
            }
        ],
    ];


    const rootData = useMemo(() => instanceData.filter((r: RowData) => !r.appiId), [instanceData, metrics]);
    const table = useMaterialReactTable({
        columns,
        data: rootData,
        getSubRows: (row: RowData) => instanceData.filter((r: RowData) => r.appiId === row.id),
        paginateExpandedRows: false,

        enableExpandAll: false, //hide expand all double arrow in column header
        enableExpanding: true, //disable expanding rows by default (replaced by a custom expand function)

        enableDensityToggle: false,
        initialState: { density: 'compact' },

        enableFullScreenToggle: false,
    });

    return (
        <>
            {loading ? (
                // Show a loading skeleton while data is being fetched
                <Box sx={{ width: '100%' }}>
                    <Skeleton variant="rectangular" width="100%" height={200} />
                    <Skeleton variant="text" width="100%" />
                    <Skeleton variant="text" width="100%" />
                    <Skeleton variant="text" width="100%" />
                </Box>
            ) : (
                <>
                    <MaterialReactTable table={table} />
                    <DetailsDialog
                        open={detailsDialogOpen}
                        onClose={() => setDetailsDialogOpen(false)}
                        title='Instance Details'
                        data={detailsData}
                    />
                    <ConfirmationDialog
                        open={confirmationDialogOpen}
                        onClose={() => setConfirmationDialogOpen(false)}
                        onConfirm={() => {
                            terminateInstance(id);
                            setConfirmationDialogOpen(false);
                        }}
                        action={ActionType.TERMINATE}
                        item={Item.INSTANCE}
                    />
                </>
            )}
        </>
    );

};

export default InstanceGrid;
