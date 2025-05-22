import { useEffect, useState } from "react";
import Box from "@mui/material/Box";
import { DataGrid, GridColDef, GridRowParams, GridRenderCellParams } from '@mui/x-data-grid';
import Typography from "@mui/material/Typography";
import { IconButton, Tooltip, LinearProgress, Skeleton } from "@mui/material";
import { getAppI, terminateAppI } from "../../api/api";
import { DropdownOption, InstanceData, OperationalStatus, ConfigStatus, ActionType, Item, InstanceGridProps, Metrics, RowData } from "../../types/Component";
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import CancelIcon from '@mui/icons-material/Cancel';
import AccessTimeFilledIcon from '@mui/icons-material/AccessTimeFilled';
import StopCircleIcon from '@mui/icons-material/StopCircle';
import MoreHorizIcon from '@mui/icons-material/MoreHoriz';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
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
    const [instanceData, setInstanceData] = useState<InstanceData[]>([]);
    const [expandedRows, setExpandedRows] = useState<{ [key: string]: boolean }>({});
    const [metrics, setMetrics] = useState<Metrics | null>(null);
    const [rowData, setRowData] = useState<RowData[]>([]);

    // Dialog variables
    const [loading, setLoading] = useState(true);
    const [detailsDialogOpen, setDetailsDialogOpen] = useState(false);
    const [detailsData, setDetailsData] = useState('');
    const [confirmationDialogOpen, setConfirmationDialogOpen] = useState(false);
    const [id, setId] = useState('');
    const [socket, setSocket] = useState<WebSocket | null>(null);

    // Table Pagination
    const [page, setPage] = useState(0);
    const [pageSize, setPageSize] = useState(0);
    const [rowCount, setRowCount] = useState(0);

    // Get the Rows to show in the DataGrid
    const getInstanceData = async () => {
        try {
            const { data } = await getAppI();
            const formattedData = data.map((d: any) => ({
                ...d,
                'id': d['appi_id'],
                'created-at': new Date(d['created-at']),
            }));
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
            socket.onmessage = (event) => {
                const data: Metrics = event.data ? JSON.parse(event.data) : {};
                setMetrics((prevMetrics) => {
                    if (!prevMetrics) {
                        prevMetrics = {}
                    }

                    for (const appi_id in data) {
                        if (!(appi_id in prevMetrics)) {
                            prevMetrics[appi_id] = {}
                        }

                        for (const container_id in data[appi_id]) {
                            prevMetrics[appi_id][container_id] = {
                                mem_load: data[appi_id][container_id].mem_load != null && data[appi_id][container_id].mem_load >= 0 ? data[appi_id][container_id].mem_load.toFixed(2) : null,
                                cpu_load: data[appi_id][container_id].cpu_load != null && data[appi_id][container_id].cpu_load >= 0  ? data[appi_id][container_id].cpu_load.toFixed(2) : null,
                                latency: data[appi_id][container_id].latency != null && data[appi_id][container_id].latency >= 0  ? data[appi_id][container_id].latency.toFixed(2) : null,
                                kdu_id: data[appi_id][container_id].kdu_id,
                                warning: data[appi_id][container_id].warning,
                                node: data[appi_id][container_id].node
                            }
                        }
                    }
                    return prevMetrics;
                });
            };
            socket.onclose = () => {
                console.log('Disconnected from WebSocket');
            };
        }
    }, [socket]);

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

    // Update the rows based on the instance data and metrics
    useEffect(() => {
        let rows: any = [];

        // Order data by created-at and apply pagination
        setRowCount(instanceData.length);
        const ordered_paginated_data = [...instanceData].sort((a, b) => {
            return b['created-at'] - a['created-at'];
        }).slice(page * pageSize, (page + 1) * pageSize);
        console.log("Page Data: ", ordered_paginated_data);

        for (const key in ordered_paginated_data) {
            // Add a row as we want the apps to be displayed
            const row_data: RowData = {
                id: ordered_paginated_data[key].id,
                expand: true,
                name: ordered_paginated_data[key].name,
                description: ordered_paginated_data[key].description,
                details: ordered_paginated_data[key].details,
                'current-meh': null,
                'cpu-load': null,
                'mem-load': null,
                latency: null,
                'created-at': ordered_paginated_data[key]['created-at'],
                'operational-status': ordered_paginated_data[key]['operational-status'],
                'config-status': ordered_paginated_data[key]['config-status'],
                warnings: null,
                actions: true
            };
            rows.push(row_data);

            if (expandedRows[ordered_paginated_data[key].id]) {
                // Add a row for each container as we want the containers to be displayed
                if ( metrics && ordered_paginated_data[key].id in metrics){
                    for (const container in metrics[ordered_paginated_data[key].id]) {
                        const row_data: RowData = {
                            id: container,
                            expand: false,
                            name: container,
                            description: "kdu: " + metrics[ordered_paginated_data[key].id][container]['kdu_id'],
                            details: '',
                            'current-meh': metrics[ordered_paginated_data[key].id][container]['node'],
                            'cpu-load': metrics[ordered_paginated_data[key].id][container]['cpu_load'],
                            'mem-load': metrics[ordered_paginated_data[key].id][container]['mem_load'],
                            latency: metrics[ordered_paginated_data[key].id][container]['latency'],
                            'created-at': null,
                            'operational-status': null,
                            'config-status': null,
                            warnings: metrics[ordered_paginated_data[key].id][container]['warning'],
                            actions: false
                        }
                        rows.push(row_data);
                    }
                }
            }
        }
        setRowData(rows);
    }, [instanceData, expandedRows, metrics, page, pageSize]);

    // Change the expanded state of a row to the opposite
    const handleExpandClick = (id: string) => {
        setExpandedRows((prev) => {
            return {
                ...prev,
                [id]: !prev[id]
            }
            
        });
    };

    // Columns for the DataGrid
    const columns: GridColDef[] = [
        {
            field: 'expand',
            headerName: '',
            width: 50,
            renderCell: (params: GridRenderCellParams) => (
                <>
                    {
                        (() => {
                            if (!params.row.expand) {
                                return null;
                            }
                            return (
                                <IconButton
                                    size="small"
                                    onClick={() => handleExpandClick(params.row.id)}
                                >
                                    {expandedRows[params.row.id] ? <ExpandLessIcon /> : <ExpandMoreIcon />}

                                </IconButton>
                            )
                            
                        })()
                    }
                </>
            ),
        },
        {
            field: 'name',
            headerName: 'Name',
            width: 200
        },
        ...minimalConfig ? [] : [
            {
                field: 'description',
                headerName: 'Description',
                flex: 1
            }
        ],
        ...minimalConfig ? [] : [
            {
                field: 'details',
                headerName: 'Details',
                flex: 1,
                renderCell: (params: any) => (
                    <Box display='flex' justifyContent='space-between' alignItems='center' width='100%'>
                        <Typography
                            variant='body2'
                            overflow='hidden'
                            textOverflow='ellipsis'
                            whiteSpace='nowrap'
                            flex='1'
                        >
                            {params.row.details}
                        </Typography>
                        <IconButton onClick={() => {
                            setDetailsDialogOpen(true);
                            setDetailsData(params.row.details);
                        }}>
                            <MoreHorizIcon />
                        </IconButton>
                    </Box >
                )
            }
        ],
        {
            field: 'current-meh',
            headerName: 'Current MEC Host',
            width: 200,
            type: 'string',
            renderCell: (params: any) => {
                const node = params.row['current-meh'];
                return (
                    <Box sx={{ position: 'relative', width: '100%' }}>
                        {node !== undefined && node !== null ? (
                            <>
                                <Typography
                                    variant="body2"
                                >
                                    {node}
                                </Typography>
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
            field: 'cpu-load',
            headerName: 'CPU (%)',
            width: 70,
            type: 'number',
            headerAlign: 'center',
            align: 'center',
            renderCell: (params: any) => {
                const cpuLoad: string = params.row['cpu-load'];
                return (
                    <Box sx={{ position: 'relative', width: '100%' }}>
                        {cpuLoad !== undefined && cpuLoad !== null ? (
                            <>
                                <LinearProgress
                                    variant="determinate"
                                    value={Number(cpuLoad)}
                                    sx={{ width: '100%', height: '30px' }}
                                    color={getLoadColor(Number(cpuLoad))}
                                />
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
            field: 'mem-load',
            headerName: 'Mem (%)',
            width: 70,
            type: 'number',
            headerAlign: 'center',
            align: 'center',
            renderCell: (params: any) => {
                const memLoad: string = params.row['mem-load'];
                return (
                    <Box sx={{ position: 'relative', width: '100%' }}>
                        {memLoad !== undefined && memLoad !== null ? (
                            <>
                                <LinearProgress
                                    variant="determinate"
                                    value={Number(memLoad)}
                                    sx={{ width: '100%', height: '30px' }}
                                    color={getLoadColor(Number(memLoad))}
                                />
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
            field: 'latency',
            headerName: 'Latency (ms)',
            width: 100,
            type: 'number',
            headerAlign: 'center',
            align: 'center',
            renderCell: (params: any) => {
                const latency: string = params.row.latency;
                return (
                    <Box sx={{ position: 'relative', width: '100%' }}>
                        {latency !== undefined && latency !== null ? (
                            <>
                                <LinearProgress
                                    variant="determinate"
                                    value={Number(latency)}
                                    sx={{ width: '100%', height: '30px' }}
                                    color={getLoadColor(Number(latency))}
                                />
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
                                    {latency}
                                </Typography>
                            </>) : (
                            <Typography variant="body2" textAlign='center'>
                                -
                            </Typography>
                        )}
                    </Box>
                )
            }
        },
        ...minimalConfig ? [] : [
            {
                field: 'created-at',
                headerName: 'Created At',
                width: 90,
                type: 'date',
                headerAlign: 'center',
                align: 'center',
                renderCell: (params: any) => (
                    params.row['created-at'] !== undefined && params.row['created-at'] !== null ? (
                        <Tooltip title={params.row['created-at'].toLocaleString()}>
                            <Typography variant="body2">
                                {params.row['created-at'].toLocaleDateString()}
                            </Typography>
                        </Tooltip>
                    ) : (
                        <Typography variant="body2" textAlign='center'>
                            -
                        </Typography>
                    )
                )
            }
        ],
        {
            field: 'operational-status',
            headerName: 'Operational Status',
            width: minimalConfig ? undefined : 100,
            headerAlign: 'center',
            flex: minimalConfig ? 1 : undefined,
            align: 'center',
            renderCell: (params) => (
                params.row['operational-status'] !== undefined && params.row['operational-status'] !== null ? (
                    renderOperationalStatus(params.row['operational-status'] as OperationalStatus)
                ) : (
                    <Typography variant="body2" textAlign='center'>
                        -
                    </Typography>
                )
            )
        },
        ...minimalConfig ? [] : [
            {
                field: 'config-status',
                headerName: 'Config Status',
                width: 100,
                headerAlign: 'center',
                align: 'center',
                renderCell: (params: any) => (
                    params.row['config-status'] !== undefined && params.row['config-status'] !== null ? (
                        renderConfigStatus(params.row['config-status'] as ConfigStatus)
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
                field: 'warnings',
                headerName: 'Warnings',
                width: 100,
                headerAlign: 'center',
                align: 'center',
                renderCell: (params: any) => {
                    const warning = params.row.warnings;

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
                field: 'actions',
                headerName: '',
                width: 150,
                sortable: false,
                headerAlign: 'center',
                align: 'center',
                renderCell: (params: any) => (
                    (
                        params.row.actions !== undefined && params.row.actions !== null ?
                        (
                            <DropdownButton
                                title='Actions'
                                options={
                                    [
                                        {
                                            label: 'Terminate',
                                            handleClick: () => {
                                                setConfirmationDialogOpen(true);
                                                setId(params.row.id as string);
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
                    <DataGrid
                        initialState={{
                            pagination: {
                              paginationModel: { pageSize: 10, page: 0 },
                            },
                          }}
                        hideFooter={minimalConfig}
                        getRowId={(row) => row.id}
                        rows={rowData} // Correct filtered row list
                        columns={columns.map((col) => ({
                            ...col,
                            sortable: false,  // Disable sorting for all columns
                        }))}
                        pagination
                        paginationMode="server" // Important for manual pagination
                        rowCount={rowCount} // Only count expanded rows
                        pageSizeOptions={[5, 10, 30, 100]}
                        onStateChange={(state) => {
                            if (state.pagination.paginationModel.pageSize >= 0) {
                                setPageSize(state.pagination.paginationModel.pageSize);
                            }
                            if (state.pagination.paginationModel.page >= 0) {
                                setPage(state.pagination.paginationModel.page);
                            }
                        }}
                        disableRowSelectionOnClick
                        sx={{
                            "&.MuiDataGrid-root .MuiDataGrid-cell:focus-within": {
                                outline: "none !important",
                            },
                            "& .MuiDataGrid-columnHeaders": {
                                backgroundColor: "#f5f5f5",
                            },
                            "& .MuiDataGrid-footerContainer": {
                                backgroundColor: "#f5f5f5",
                            },
                            "& .MuiDataGrid-row": {
                                backgroundColor: "#f5f5f5",
                            },
                            display: 'grid',
                            "& .MuiDataGrid-row.expandedRow": {
                                backgroundColor: "#f0f0f0",
                            },
                        }}
                        getRowClassName={(params) =>
                            params.row.expand ? "expandedRow" : ""
                        }
                    />
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